# This extension returns extra objects
# iso_list: for keeping track of all members of the tree
# eic_list: for keeping track of the tree structure, the immediate children
# of each member

import numpy as n
import scipy.ndimage as sn
import time
from itertools import islice
from collections import deque

from fiso import fiso

# printing extra diagnostic messages
verbose = True
# how to determine neighbors of boundary cells
timer = fiso.timer
setup = fiso.setup

def find(data,cut=''):
    mfw,order,cutoff,pcn = setup(data,cut)
    #iso dict and labels setup
    iso_dict = {}
    labels = -n.ones(len(order),dtype=int) #indices are real index locations
    #inside loop, labels are accessed by labels[order[i]]
    for mini in mfw:
        iso_dict[mini] = deque([mini])
    labels[mfw] = mfw
    possible_isos = set(mfw) #real index

    # TS: tree specific
    iso_list = []
    eic_list = [] #exclusive immediate children
    parent_dict = {}
    child_dict = {}
    for iso in possible_isos:
        parent_dict[iso] = iso
        child_dict[iso] = deque([iso])
        iso_list.append(iso)
        eic_list.append([])
    active_isos = set()
    # TS: tree specific

    indices = iter(range(cutoff))

    min_active = 1
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
                min_active = 0
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
            # There are 2 or more neighbors to deal with
            # TS
            merge(active_isos,nls0,orderi,iso_dict,child_dict,parent_dict,iso_list,eic_list,labels)
            # TS
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
            elif orderi in possible_isos:
                labels[orderi] = orderi
                active_isos.add(orderi)
                possible_isos.discard(orderi)
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
            active_isos.discard(nlsi)

def merge(active_isos,parents,orderi,iso_dict,child_dict,parent_dict,iso_list,eic_list,labels):
    # merge removes deactivated parents
    # subsume removes deactivated parents
    # hence, inactive parents must have come from collide
    # first check for inactive parents which must have come from collide
    # if any inactive parents, collide
    # if all parents are active, first subsume smallest isos. 
    if set(parents) <= active_isos:
        tree_subsume(active_isos,parents,orderi,iso_dict,child_dict,parent_dict,iso_list,eic_list,labels)
    else:
        collide(active_isos,parents)
        return 
    eic = list(set(parents) & active_isos)
    # eic = list(parents)
    # start new iso, assign it to be its own child and parent
    iso_dict[orderi] = deque([orderi])
    labels[orderi] = orderi
    child_dict[orderi] = deque([orderi])
    parent_dict[orderi] = orderi

    # new parent iso is active
    active_isos.add(orderi)
    iso_list.append(orderi)
    eic_list.append(eic)
    # exclusive immediate children
    for iso in eic:
        # new parent orderi owns all children of all merging isos
        # orderi's children is children
        child_dict[orderi] += child_dict[iso]
        # children's parent is orderi.
        for child in child_dict[iso]:
            parent_dict[child] = orderi
            # deactivate iso
        active_isos.discard(iso)
    

def tree_subsume(active_isos,parents,orderi,iso_dict,child_dict,parent_dict,iso_list,eic_list,labels):
    min_cells = 27
    eic_dict = dict(zip(iso_list,eic_list))
    subsume_set = set()
    len_list = [None] * len(parents)
    cell_list = [None] * len(parents)
    for i in range(len(parents)):
        parent = parents[i]
        lidp = len(iso_dict[parent])
        if lidp < min_cells:
            # too small, try making bigger
            cell_list[i] = recursive_members(iso_dict,eic_dict,parent)
            lidp = len(cell_list[i])
            if lidp < min_cells:
                # still too small 
                subsume_set.add(i)
        else: # big enough
            cell_list[i] = iso_dict[parent]
        len_list[i] = lidp
    largest_i = n.argmax(len_list)
    largest_parent = parents[largest_i]
    subsume_set.discard(largest_i)
    # add too small to largest
    for i in subsume_set:
        # add smaller iso cells to larger dict
        iso_dict[largest_parent] += cell_list[i]
        # relabel smaller iso cells to larger
        labels[cell_list[i]] = largest_parent
        # delete smaller iso
        active_isos.remove(parents[i])
        iso_dict.pop(parents[i])
        # note any children of smaller iso would be too small 
        # and be previously subsumed
    
# Keep ordered list of isos [ ]
# Keep ordered list of lists [ ]. Each list is immediate children.
# When considering merges in post, move along ordered list of isos
# and resolve from bottom to top. 1 pass.
# Each iso ixs processed before its parents.

def recursive_num_members(iso_dict,eic_dict,iso):
    output = len(iso_dict[iso])
    for child_iso in eic_dict[iso]:
        output += recursive_num_members(iso_dict,eic_dict,child_iso)
    return output

def recursive_members(iso_dict,eic_dict,iso):
    output = []
    output += iso_dict[iso]
    for child_iso in eic_dict[iso]:
        output += recursive_members(iso_dict,eic_dict,child_iso)
    return output
