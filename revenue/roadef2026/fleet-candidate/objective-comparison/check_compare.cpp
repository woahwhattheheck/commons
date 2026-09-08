// SPDX-License-Identifier: MIT
#include "quantized_compare.hpp"
#include <cassert>
#include <cmath>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <random>
#include <string>
using Vec = std::vector<long long>;
static std::uint64_t checked = 0;
static delve::CompareStats stats;
static bool oracle(Vec& b, Vec& a) {
    std::sort(b.begin(), b.end(), std::greater<long long>());
    std::sort(a.begin(), a.end(), std::greater<long long>());
    return a < b;
}
static void check(const Vec& b, const Vec& a) {
    Vec ob=b, oa=a, fb=b, fa=a;
    const bool expect=oracle(ob,oa), actual=delve::quantized_improves(fb,fa,&stats);
    if (expect!=actual) { std::cerr<<"comparison mismatch case "<<checked<<"\n"; std::exit(1); }
    std::sort(fb.begin(),fb.end(),std::greater<long long>());
    std::sort(fa.begin(),fa.end(),std::greater<long long>());
    if (fb!=ob||fa!=oa) { std::cerr<<"content changed\n"; std::exit(1); }
    ++checked;
}
static Vec digits(int x, int n) {
    Vec out(n); for (auto& v:out) { v=x%4; x/=4; } return out;
}
int main() {
    for (int n=0, count=1;n<=4;++n,count*=4)
        for(int b=0;b<count;++b) for(int a=0;a<count;++a) check(digits(b,n),digits(a,n));
    const long long lo=std::numeric_limits<long long>::min(), hi=std::numeric_limits<long long>::max();
    for(const Vec& b:std::vector<Vec>{{},{0},{lo,hi,hi},{hi,lo,lo},{hi,hi,0}})
        for(const Vec& a:std::vector<Vec>{{},{0},{lo,hi,hi},{hi,lo,lo},{hi,hi,0}}) check(b,a);
    std::mt19937_64 rng(827193);
    for (int k=0;k<100000;++k) {
        std::size_t n=rng()%193; Vec b(n),a(n);
        for(auto& v:b) v=static_cast<long long>(rng()%100003);
        a=b;
        switch(k%5) {
        case 0: for(auto& v:a) v=static_cast<long long>(rng()%100003); break;
        case 1: if(n) { a[rng()%n]=100010; } break;
        case 2: if(n) { std::fill(b.begin(),b.end(),123); a=b; a[rng()%n]=122; } break;
        case 3: std::shuffle(a.begin(),a.end(),rng); break;
        case 4: if(n>3) { b[0]=a[0]=1000000; a[1]=0; } break;
        }
        check(b,a);
    }
    // Full-objective cancellation: unchanged entries may surround the local
    // changed loads at any rank, but cannot change the strict comparison.
    for (int k=0;k<20000;++k) {
        Vec b,a,common;
        for(int j=0,n=1+rng()%80;j<n;++j) {
            const double load=static_cast<double>(rng()%10000000)/1000000.0;
            const double change=(static_cast<long long>(rng()%10000)-5000)/1000000.0;
            b.push_back(static_cast<long long>(std::floor(std::max(0.0,load-1e-10)*1e6)));
            a.push_back(static_cast<long long>(std::floor(std::max(0.0,load+change+1e-10)*1e6)));
        }
        for(int j=0,n=rng()%100;j<n;++j) common.push_back(static_cast<long long>(rng()%10000000));
        Vec globalb=b,globala=a,localb=b,locala=a;
        globalb.insert(globalb.end(),common.begin(),common.end());
        globala.insert(globala.end(),common.begin(),common.end());
        if(oracle(globalb,globala)!=delve::quantized_improves(localb,locala)) {
            std::cerr<<"global cancellation mismatch\n";return 1;
        }
        check(b,a);
    }
    std::cout<<"{\"checks\":"<<checked<<",\"max_decisive\":"<<stats.maxima
             <<",\"count_decisive\":"<<stats.counts<<",\"fallback\":"<<stats.fallback<<"}\n";
}
