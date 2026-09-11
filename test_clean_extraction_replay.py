import hashlib,io,json,os,stat,tarfile,tempfile,unittest,warnings,zipfile
from pathlib import Path
from clean_extraction_replay import ReplayError,main,replay_archive

def canon(v):return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def manifest_for(files):
    rows=[{"path":p,"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}for p,b in sorted(files.items())]
    payload={"schema":"commons-deliverable-manifest/v1","files":rows,"acceptance":[{"id":"A1","description":"Files replay exactly","paths":sorted(files)}]}
    return json.dumps({**payload,"manifest_sha256":hashlib.sha256(canon(payload)).hexdigest()},sort_keys=True).encode()
def write_zip(path,files):
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED)as z:
        for n,b in files.items():z.writestr(n,b)
def write_tar(path,files):
    with tarfile.open(path,"w:gz")as t:
        for n,b in files.items():i=tarfile.TarInfo(n);i.size=len(b);t.addfile(i,io.BytesIO(b))
class T(unittest.TestCase):
    def setUp(self):
        self.files={"README.txt":b"delivery\n","dist/app.js":b"export const n=7;\n","types/app.d.ts":b"export declare const n:number;\n"};self.manifest=manifest_for(self.files)
    def test_valid_zip_and_tar(self):
        for ext,writer,fmt in(("zip",write_zip,"zip"),("tar.gz",write_tar,"tar")):
            with self.subTest(ext=ext),tempfile.TemporaryDirectory()as td:
                p=Path(td)/f"b.{ext}";writer(p,self.files);r=replay_archive(p,self.manifest);self.assertTrue(r["verified"]);self.assertTrue(r["fresh_extraction"]);self.assertEqual(fmt,r["archive_format"]);self.assertEqual(3,r["files_verified"])
    def test_changed_missing_extra(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td)/"b.zip";f=dict(self.files);f["dist/app.js"]=b"changed";write_zip(p,f)
            with self.assertRaisesRegex(ReplayError,"changed=.*dist/app.js"):replay_archive(p,self.manifest)
            f=dict(self.files);del f["README.txt"];f["EXTRA.txt"]=b"x";write_zip(p,f)
            with self.assertRaisesRegex(ReplayError,"missing=.*README.*extra=.*EXTRA"):replay_archive(p,self.manifest)
    def test_zip_guards(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);cases=[]
            for name in("../x","a\\b"):
                p=root/(hashlib.md5(name.encode()).hexdigest()+".zip");write_zip(p,{name:b"x"});cases.append((p,"archive path"))
            p=root/"dup.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with zipfile.ZipFile(p,"w")as z:z.writestr("README.txt",b"1");z.writestr("README.txt",b"2")
            cases.append((p,"duplicate archive"));p=root/"link.zip";i=zipfile.ZipInfo("link");i.create_system=3;i.external_attr=(stat.S_IFLNK|0o777)<<16
            with zipfile.ZipFile(p,"w")as z:z.writestr(i,b"README.txt")
            cases.append((p,"ZIP symlink"));p=root/"type.zip";i=zipfile.ZipInfo("looks-file");i.create_system=3;i.external_attr=(stat.S_IFDIR|0o755)<<16
            with zipfile.ZipFile(p,"w")as z:z.writestr(i,b"")
            cases.append((p,"type metadata"))
            for archive,msg in cases:
                with self.subTest(msg=msg),self.assertRaisesRegex(ReplayError,msg):replay_archive(archive,self.manifest)
    def test_tar_guards(self):
        for typ,msg in((tarfile.SYMTYPE,"symlink"),(tarfile.LNKTYPE,"hardlink"),(tarfile.FIFOTYPE,"special")):
            with self.subTest(msg=msg),tempfile.TemporaryDirectory()as td:
                p=Path(td)/"b.tar"
                with tarfile.open(p,"w")as t:i=tarfile.TarInfo("x");i.type=typ;i.linkname="README.txt";t.addfile(i)
                with self.assertRaisesRegex(ReplayError,msg):replay_archive(p,self.manifest)
    def test_manifest_guards(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td)/"b.zip";write_zip(p,self.files);d=json.loads(self.manifest);d["manifest_sha256"]="0"*64
            with self.assertRaisesRegex(ReplayError,"digest mismatch"):replay_archive(p,json.dumps(d).encode())
            d=json.loads(self.manifest);d["acceptance"][0]["paths"]=["missing.txt"];payload={k:d[k]for k in("schema","files","acceptance")};d["manifest_sha256"]=hashlib.sha256(canon(payload)).hexdigest()
            with self.assertRaisesRegex(ReplayError,"references absent"):replay_archive(p,json.dumps(d).encode())
            files={"A.txt":b"a","a.txt":b"b"};write_zip(p,files)
            with self.assertRaisesRegex(ReplayError,"case-fold ambiguous manifest"):replay_archive(p,manifest_for(files))
    def test_limits(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td)/"b.zip";write_zip(p,self.files)
            with self.assertRaisesRegex(ReplayError,"file count"):replay_archive(p,self.manifest,max_files=2)
            with self.assertRaisesRegex(ReplayError,"manifest bytes"):replay_archive(p,self.manifest,max_uncompressed_bytes=1)
            one={"payload.txt":b"x"}
            with zipfile.ZipFile(p,"w")as z:z.writestr("a/",b"");z.writestr("b/",b"");z.writestr("payload.txt",b"x")
            with self.assertRaisesRegex(ReplayError,"member count"):replay_archive(p,manifest_for(one),max_files=2)
            write_zip(p,{"payload.txt":b"xx"})
            with self.assertRaisesRegex(ReplayError,"declared.*limits"):replay_archive(p,manifest_for(one),max_uncompressed_bytes=1)
    def test_symlink_archive(self):
        if not hasattr(os,"symlink"):self.skipTest("no symlink")
        with tempfile.TemporaryDirectory()as td:
            r=Path(td);real=r/"real.zip";link=r/"link.zip";write_zip(real,self.files);os.symlink(real,link)
            with self.assertRaises(ReplayError):replay_archive(link,self.manifest)
    def test_cli_no_alias_no_clobber(self):
        with tempfile.TemporaryDirectory()as td:
            r=Path(td);a=r/"b.zip";m=r/"m.json";o=r/"r.json";write_zip(a,self.files);m.write_bytes(self.manifest);self.assertEqual(0,main([str(a),"--manifest",str(m),"--output",str(o)]));self.assertTrue(json.loads(o.read_text())["verified"])
            with self.assertRaisesRegex(ReplayError,"already exists"):main([str(a),"--manifest",str(m),"--output",str(o)])
            for bad in(a,m):
                with self.assertRaisesRegex(ReplayError,"must not alias"):main([str(a),"--manifest",str(m),"--output",str(bad)])
if __name__=="__main__":unittest.main()
