"""Fixed two-hop exclusion and boundary-cost margin; no posterior guarantee."""
from dataclasses import dataclass
import math
import networkx as nx
import numpy as np
import pymatching
from .predecoder import edges_from_dem


@dataclass(frozen=True)
class GuardedEdge:
    a: int
    b: int
    mask: int
    guard: tuple
    boundary_margin: float


def compile_guarded(dem,guard_hops=2,boundary_odds_margin=10):
    if type(guard_hops) is not int or guard_hops<1 or not math.isfinite(boundary_odds_margin) or boundary_odds_margin<1:
        raise ValueError('guard_hops>=1 and finite boundary odds margin>=1 required')
    boundary=dem.num_detectors
    graph=nx.Graph();graph.add_nodes_from(range(boundary+1))
    for a,b,data in pymatching.Matching.from_detector_error_model(dem).edges():
        weight=float(data['weight'])
        if not math.isfinite(weight) or weight<0:
            return [],{'fallback':'negative_or_nonfinite_matching_weight','candidates':0}
        mask=sum(1<<bit for bit in data['fault_ids'])
        graph.add_edge(a,boundary if b is None else b,weight=weight,mask=mask)
    distances=nx.single_source_dijkstra_path_length(graph,boundary,weight='weight')
    original=edges_from_dem(dem);compiled=[];rejected=0
    neighborhoods={node:set(nx.single_source_shortest_path_length(graph,node,cutoff=guard_hops)) for node in range(boundary)}
    for a,b,mask in original:
        if not graph.has_edge(a,b) or graph[a][b]['mask']!=mask:
            rejected+=1;continue
        margin=distances.get(a,math.inf)+distances.get(b,math.inf)-graph[a][b]['weight']
        if margin<math.log(boundary_odds_margin):
            rejected+=1;continue
        guard=tuple(sorted((neighborhoods[a]|neighborhoods[b])-{a,b,boundary}))
        compiled.append(GuardedEdge(a,b,mask,guard,margin))
    return compiled,dict(fallback=None,original_candidates=len(original),candidates=len(compiled),
                         rejected_by_cost_or_mask=rejected,guard_hops=guard_hops,
                         boundary_odds_margin=boundary_odds_margin)


def guarded_scalar(syndrome,edges,observables):
    original=np.asarray(syndrome,dtype=bool)
    residual=original.copy();frame=np.zeros(observables,dtype=bool);decisions=[]
    used=set()
    for edge in edges:
        if not original[edge.a] or not original[edge.b] or any(original[index] for index in edge.guard):continue
        if edge.a in used or edge.b in used:raise ValueError('guard compiler produced overlapping choices')
        used.update((edge.a,edge.b));residual[edge.a]^=True;residual[edge.b]^=True
        for bit in range(observables):frame[bit]^=bool(edge.mask & (1<<bit))
        decisions.append((edge.a,edge.b,edge.mask))
    return residual,frame,decisions


def guarded_batch(syndromes,edges,observables,chunk_size=4096):
    syndromes=np.asarray(syndromes,dtype=bool)
    if syndromes.ndim!=2 or chunk_size<1 or observables<0:raise ValueError('invalid batch dimensions')
    residual=syndromes.copy();frames=np.zeros((len(syndromes),observables),dtype=bool)
    for start in range(0,len(syndromes),chunk_size):
        stop=min(start+chunk_size,len(syndromes))
        original=np.ascontiguousarray(syndromes[start:stop].T)
        output=original.copy();frame=np.zeros((observables,stop-start),dtype=bool)
        for edge in edges:
            selected=original[edge.a] & original[edge.b]
            if edge.guard:selected &= ~original[list(edge.guard)].any(axis=0)
            output[edge.a]^=selected;output[edge.b]^=selected
            for bit in range(observables):
                if edge.mask & (1<<bit):frame[bit]^=selected
        residual[start:stop]=output.T;frames[start:stop]=frame.T
    return residual,frames
