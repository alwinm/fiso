# This extension returns extra objects
# iso_list: for keeping track of all members of the tree
# eic_list: for keeping track of the tree structure, the immediate children
# of each member

import numpy as n
import scipy.ndimage as sn
import time
from itertools import islice
import itertools
from collections import deque

import fiso

# printing extra diagnostic messages
verbose = True
# how to determine neighbors of boundary cells
timer = fiso.timer
setup = fiso.setup

def find(data,cut=''):
    iso_dict,labels,active_isos,order,cutoff,pcn = setup(data,cut)

    iso_list = []
    eic_list = [] #exclusive immediate children

    # TS: tree specific
    parent_dict = {}
    child_dict = {}
    for iso in active_isos:
        parent_dict[iso] = iso
        child_dict[iso] = deque([iso])
        iso_list.append(iso)
        eic_list.append([])
    # TS: tree specific

    indices = iter(range(cutoff))

    min_active = 0
    for i in indices:
        orderi = order[i]
        nls = set(labels[
            pcn[orderi]
        ])
        nls0 = nls.copy()
        nls0.discard(-1)
        nls0.discard(-2)
        nls0 = list(set(
            [parent_dict[nlsi] for nlsi in nls0]
        ))
        nnc = len(nls0)
        # number of neighbors in isos
        # first note this cell has been explored
        labels[orderi] = -2
        if (nnc > 0):
            if -2 in nls:
                # a neighbor is previously explored but not isod (boundary), deactivate isos
                collide(active_isos,nls0)
                if len(active_isos) == min_active:
                    next(islice(indices,cutoff-i-1,cutoff-i-1),None)
                continue
            if (nnc == 1):
                # only 1 neighbor, inherit
                inherit = nls0[0]
                if inherit in active_isos:
                    labels[orderi] = inherit
                    iso_dict[inherit].append(orderi)
                    # inherit from neighbor, only 1 is positive/max
                continue
            elif (nnc == 2):
                if set(nls0) <= active_isos:
                    # check smaller neighbor if it is too small
                    l0 = len(iso_dict[nls0[0]])
                    l1 = len(iso_dict[nls0[1]])
                    if min(l0,l1) < 27:
                        subsume(l0,l1,orderi,nls0,iso_dict,labels,active_isos)
                        continue
            # There are 2 or more large neighbors to deactivate
            # isoi is real index
            # TS
            merge(active_isos,nls0,orderi,iso_dict,child_dict,parent_dict,iso_list,eic_list)
            # TS
            # collide(active_isos,nls0)
            if verbose:
                print(i,' of ',cutoff,' cells ',
                      len(active_isos),' minima')
            if len(active_isos) == min_active:
                next(islice(indices,cutoff-i-1,cutoff-i-1),None)
                # skip up to next iso or end
        else:
            # no lesser neighbors
            if orderi in active_isos:
                labels[orderi] = orderi
    dt = timer('loop finished for ' + str(cutoff) + ' items')
    if verbose: print(str(dt/i) + ' per cell')
    if verbose: print(str(dt/cutoff) + ' per total cell')
    return iso_dict,labels,iso_list,eic_list

#if alone, start new iso
#if neighbor is in an active iso, add to iso
#if neighor is in an inactive iso, don't add to iso
#if 2 or more neighbors are in different isos, dont add to a iso.
# Q: What happens when a child's parent is subsumed? Their new parent is the subsumer
# Q: What happens when a child's parent is deactivated in collision with boundary? 
# Who is their new parent?
# During merge, parents that get inactivated are replaced with active parent.
# When a child's parent is inactive 
# to turn tree into normal, just set merge to collide

def collide(active_isos,nls0,*args):
    for nlsi in nls0:
        if nlsi in active_isos:
            active_isos.remove(nlsi)

def subsume(l0,l1,orderi,nls0,iso_dict,labels,active_isos):
    smaller = n.argmin([l0,l1])
    larger = 1-smaller
    #add smaller iso cells to larger dict
    iso_dict[nls0[larger]] += iso_dict[nls0[smaller]]
    #relabel smaller iso cells to larger
    labels[iso_dict[nls0[smaller]]] = nls0[larger]
    active_isos.remove(nls0[smaller])
    iso_dict.pop(nls0[smaller])

    labels[orderi] = nls0[larger]
    iso_dict[nls0[larger]].append(orderi)
   
def merge(active_isos,parents,orderi,iso_dict,child_dict,parent_dict,iso_list,eic_list):
    merge_bool = False
    eic = []
    for iso in parents:
        if iso in active_isos:
            merge_bool = True
            eic.append(iso)
        else:
            print('Unexpected error: inactive parent')
    if merge_bool:
        # start new iso, assign it to be its own child and parent
        iso_dict[orderi] = deque([orderi])
        child_dict[orderi] = deque([orderi])
        parent_dict[orderi] = orderi
        # new parent iso is active
        active_isos.add(orderi)
        iso_list.append(orderi)
        eic_list.append(eic)
        # exclusive immediate children
        for iso in eic:
            # new parent orderi owns all children of all merging isos
            # children's parent is orderi.
            # orderi's children is children
            for child in child_dict[iso]:
                parent_dict[child] = orderi
            child_dict[orderi] += child_dict[iso]
            # deactivate iso
            active_isos.remove(iso)

# Keep ordered list of isos [ ]
# Keep ordered list of lists [ ]. Each list is immediate children.
# When considering merges in post, move along ordered list of isos
# and resolve from bottom to top. 1 pass.
# Each iso is processed before its parents.
