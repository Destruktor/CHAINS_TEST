/*========================================================================

  File: HREA.h

  Program HREA - Version 1.1 - July 1999

  ========================================================================

  This module contains an implementation of the Recursive Enumeration
  Algorithm (REA) that enumerates (by increasing weight) the N shortest
  paths in weighted graphs. The algorithm is described in: 

    "Computing the K Shortest Paths: a New Algorithm and an
    Experimental Comparison" by Victor Jimenez and Andres Marzal,
    3rd Workshop on Algorithm Engineering, London, July 1999.
    To be published by Springer-Verlag in the LNCS series.

  In this implementation the set of candidates associated to each node
  is implemented using the array  of pointers to incoming arcs, and is
  in part unsorted and in part structured as a binary heap. Initially,
  the full  array is  unsorted; whenever a  candidate in the  array is
  selected, the next path obtained  from it (if it exists) is inserted
  in the  heap part.   The best candidate  must be chosen  between the
  best candidate  in the heap and  the best candidate  in the unsorted
  part.  The best candidate in the unsorted part is computed only when
  it is unknown, and the loop that searches for it is used to annotate
  also  the  second  best  candidate.  This  "hybrid"  data  structure
  (therefore the  name HREA) tries  to get the asymptotic  behavior of
  heaps without paying  initially a high cost for  heapifying them. In
  practice it runs faster than REA in some cases.

  ========================================================================

    Copyright (C) 1999 Victor Jimenez and Andres Marzal

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program (file COPYING); if not, write to the Free
    Software Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

    You can contact the authors at:

           Victor Jimenez and Andres Marzal
           Dept. de Informatica, Universitat Jaume I, Castellon, Spain
           {vjimenez,amarzal}@inf.uji.es

    Updated information about this software will be available at the
    following www address:

           http://terra.act.uji.es/REA
 
  ========================================================================= */


#ifndef _HREA_H_INCLUDED

#define COST_TYPE int     /* You can change this type but you should verify
                             its use in printf's, scanf's and castings */

#define INFINITY_COST 100000000 /* Instead of INT_MAX, to avoid overflow  */
                                /* when adding some cost to INFINITY_COST */


/* The following data structures represent a graph in memory providing
   access to incoming and outgoing arcs for each node, and also allow
   to represent multiple shortest paths from the initial node to each node. 
*/


typedef struct Path {
  COST_TYPE   cost;      /* Path cost                                         */
  struct Node *lastNode; /* Node in which this path ends                      */
  struct Path *backPath; /* Prefix path, ending in a predecessor node         */
  struct Path *nextPath; /* Next path in the list of computed paths from the  */
                         /* initial node to the node in which this paths ends */
} Path;   

typedef struct Arc {
  COST_TYPE   cost;      /* Arc cost         */
  struct Node *source;   /* Source node      */
  struct Node *dest;     /* Destination node */
  struct Path *nextCand;
} Arc;  

typedef struct Arc *PtrArc;


typedef struct Node {
  int    name;              /* An integer in the range 1..graph.numberNodes */
  int    numberArcsOut;     /* Number of arcs that leave the node           */
  PtrArc *firstArcOut;      /* Pointer to an element in graph.arcOut        */
  int    numberArcsIn;      /* Number of arcs that reach the node           */
  PtrArc *firstArcIn;       /* Pointer to an element in graph.arcIn         */
  Path   *bestPath;         /* First path in the list of computed paths     */
                            /* from the initial node to this node           */
  struct Arc  *bestArcIn;   /* Last arc in the best path                    */
#define heap  firstArcIn    /* Set of candidate paths (binary heap part)    */
  int         heapSize;     /* Current size of the heap part                */
  int         listHeadSize; /* Takes values 0, 1 or 2 indicating how many   */
                            /* best values of the unsorted part are known.  */
} Node;


typedef struct Graph {
  int    numberNodes;  /* Number of nodes in the graph                        */
  int    numberArcs;   /* Number of arcs in the graph                         */
  Node   *initialNode; /* The node from which all paths depart                */
  Node   *finalNode;   /* The node to which the K shortest paths are required */
  Node   *node;        /* Nodes, with node named i in position i-1            */
  Arc    *arc;         /* Arcs sorted by destination node                     */
  PtrArc *arcIn;       /* Pointers to arcs, sorted by destination node        */
  PtrArc *arcOut;      /* Pointers to arcs, sorted by source node             */
}  Graph;

extern Path *CreatePath (Node *node, Path *backPath, COST_TYPE cost);

#define _HREA_H_INCLUDED
#endif
