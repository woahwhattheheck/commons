// SPDX-License-Identifier: MIT
// Compiled against exact extracted old/new Solver::distance method bodies.
#include <algorithm>
#include <atomic>
#include <chrono>
#include <climits>
#include <cstdlib>
#include <iostream>
#include <new>
#include <random>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>
#ifdef ROADEF_COUNT_ALLOCATIONS
static std::atomic<unsigned long long> allocations{0};
void* operator new(std::size_t n) {
    allocations.fetch_add(1, std::memory_order_relaxed);
    if (void* p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
#endif
using Route=std::vector<int>;
struct Demand { int from, to; };
struct Original {
    std::vector<Demand> demands;
#include "old_method.inc"
};
struct Candidate {
    std::vector<Demand> demands;
#include "new_method.inc"
};
struct Case { int d; Route a,b; };
static std::set<std::pair<int,int>> edges(const Demand& d,const Route& r) {
    std::set<std::pair<int,int>> out;
    int from=d.from;
    for(int v:r) { out.emplace(from,v); from=v; }
    out.emplace(from,d.to);
    return out;
}
static int oracle(const Demand& d,const Route& a,const Route& b) {
    auto x=edges(d,a),y=edges(d,b);
    std::vector<std::pair<int,int>> diff;
    std::set_symmetric_difference(x.begin(),x.end(),y.begin(),y.end(),std::back_inserter(diff));
    return int(diff.size());
}
static void enumerate(std::vector<Route>& out,Route& prefix,int alphabet,int depth) {
    out.push_back(prefix);
    if(!depth)return;
    for(int x=0;x<alphabet;++x) {prefix.push_back(x);enumerate(out,prefix,alphabet,depth-1);prefix.pop_back();}
}
static volatile unsigned long long sink=0;
template<class S> static double bench(const S& solver,const std::vector<Case>& cases,int reps) {
    unsigned long long sum=0;
    auto start=std::chrono::steady_clock::now();
    for(int r=0;r<reps;++r)for(const auto& c:cases)sum+=solver.distance(c.d,c.a,c.b);
    double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    sink=sum;
    return seconds;
}
int main(int argc,char**argv) {
    int reps=argc>1?std::stoi(argv[1]):20;
    if(reps<0||reps>10000)throw std::runtime_error("invalid repetitions");
    Original old;Candidate now;
    for(int a=0;a<4;++a)for(int b=0;b<4;++b)old.demands.push_back({a,b});
    old.demands.push_back({INT_MIN,INT_MAX});now.demands=old.demands;
    std::vector<Route> routes;Route prefix;enumerate(routes,prefix,4,3);
    unsigned long long count=0,checksum=0;
    auto check=[&](int d,const Route& a,const Route& b){
        int x=old.distance(d,a,b),y=now.distance(d,a,b),z=oracle(old.demands[d],a,b);
        if(x!=y||y!=z||y!=now.distance(d,b,a)||now.distance(d,a,a)!=0)
            throw std::runtime_error("distance mismatch at case "+std::to_string(count));
        ++count;checksum+=y;
    };
    for(int d=0;d<16;++d)for(const auto&a:routes)for(const auto&b:routes)check(d,a,b);
    const auto exhaustive=count;
    std::mt19937 rng(20260908);
    std::vector<Case> short_cases,long_cases;
    for(int k=0;k<20000;++k){
        Case c; c.d=int(rng()%old.demands.size());
        for(unsigned i=0,n=rng()%8;i<n;++i)c.a.push_back(int(rng()%12)-4);
        for(unsigned i=0,n=rng()%8;i<n;++i)c.b.push_back(int(rng()%12)-4);
        if(k%11==0)c.b=c.a;
        if(k%41==0)c.a={INT_MIN,INT_MAX,INT_MIN,INT_MAX};
        check(c.d,c.a,c.b);short_cases.push_back(std::move(c));
    }
    for(int k=0;k<2000;++k){
        Case c;c.d=int(rng()%old.demands.size());
        for(unsigned i=0,n=8+rng()%41;i<n;++i)c.a.push_back(int(rng()%12)-4);
        for(unsigned i=0,n=rng()%49;i<n;++i)c.b.push_back(int(rng()%12)-4);
        check(c.d,c.a,c.b);long_cases.push_back(std::move(c));
    }
    long long old_short=-1,new_short=-1,old_long=-1,new_long=-1;
#ifdef ROADEF_COUNT_ALLOCATIONS
    auto alloc=[&](const auto&s,const auto&cases){
        auto start=allocations.load();unsigned long long total=0;
        for(const auto&c:cases)total+=s.distance(c.d,c.a,c.b);
        sink=total;return allocations.load()-start;
    };
    old_short=alloc(old,short_cases);new_short=alloc(now,short_cases);
    old_long=alloc(old,long_cases);new_long=alloc(now,long_cases);
    if(new_short!=0||old_long!=new_long)throw std::runtime_error("allocation contract mismatch");
#endif
    std::cout<<"{\"comparisons\":"<<count<<",\"exhaustive\":"<<exhaustive
             <<",\"short_random\":20000,\"long_random\":2000,\"checksum\":"<<checksum
             <<",\"old_short_allocations\":"<<old_short<<",\"new_short_allocations\":"<<new_short
             <<",\"old_long_allocations\":"<<old_long<<",\"new_long_allocations\":"<<new_long
             <<",\"rounds\":[";
    for(int round=0;round<9&&reps;++round){
        double a,b;
        if(round%2){b=bench(now,short_cases,reps);a=bench(old,short_cases,reps);}
        else{a=bench(old,short_cases,reps);b=bench(now,short_cases,reps);}
        if(round)std::cout<<',';
        std::cout<<"{\"original_seconds\":"<<a<<",\"candidate_seconds\":"<<b<<"}";
    }
    std::cout<<"],\"calls_per_arm_per_round\":"<<short_cases.size()*reps<<"}\n";
}
