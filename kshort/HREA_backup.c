/*========================================================================

  File: HREA.c

  Program HREA - Version 1.1 - July 1999

  ========================================================================

  This module contains an implementation of the Recursive Enumeration
  Algorithm (REA) that enumerates (by increasing weight) the N shortest
  paths in weighted graphs. The algorithm is described in: 

    "Computing the K Shortest Paths: a New Algorithm and an
    Experimental Comparison" by Victor Jimenez and Andres Marzal,
    3rd Workshop on Algorithm Engineering, London, July 1999.
    To be published by Springer-Verlag in the LNCS series.

  The sets of candidate paths are implemented using a hybrid structure
  that is in part unsorted and in part a binary heap. See HREA.h for
  more details.

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

#define VERSION "1.1"

#include <stdlib.h>
#include <stdio.h>
#include <time.h>  
#include <unistd.h>  

#ifdef DEBUG
#include <assert.h>
#endif

#include <HREA.h>
#include <loadgraph.h>
#include <dijkstra.h>
#include <chronometer.h>


/*============================================================================
  GLOBAL VARIABLES
  ============================================================================*/

/* For experimental purposes we avoid to use the malloc system for new paths */
/* New paths are taken from this buffer by the function CreatePath           */

#define MAX_PATHS 10000000
Path pathsBuffer[MAX_PATHS];
int  numberUsedPaths = 0;
Path *firstFreePath = pathsBuffer;


/*============================================================================*/
__inline__ Path *CreatePath (Node *node, Path *backPath, COST_TYPE cost) {

  Path   *newPath;
  
#ifdef DEBUG
  assert (node != NULL);
#endif
  
  if (++numberUsedPaths > MAX_PATHS) {
    fprintf (stderr, "Redefine MAX_PATHS");
    exit(1);
  }
  newPath = firstFreePath++;
  
  newPath->backPath = backPath;
  newPath->cost     = cost;
  newPath->lastNode = node;
  newPath->nextPath = NULL;
  
  return newPath;
  
}


/*============================================================================*/
void PrintPath (Path *path) {
  /* Prints the path in reverse order (with the final node first). */
  Path *backPath;
  
#ifdef DEBUG
  assert (path != NULL); 
#endif
 if (path->cost < INFINITY_COST) {
  for (backPath = path; backPath != NULL; backPath = backPath->backPath)
    printf ("%i-", backPath->lastNode->name);
  printf (" \t(Cost: %i)", path->cost);
 }
  
}

#define COST(_arc_) (((_arc_)->nextCand->cost + (_arc_)->cost))

/*============================================================================*/
__inline__ void UpdateHeap (Node *node) {
  /* After the element in the top of the heap (position 0) has been 
     replaced by a new one, this function restores the heap property.
     in worst case time logarithmic with the heap size.
     The heap size does not change. */
  
  register Arc * newElt = node->heap[0];
  register COST_TYPE newCost = COST(newElt);
  register int heapSize = node->heapSize;
  register int j = 1;
  while (j<heapSize) {
    register PtrArc * cand = node->heap + j;
    if (j<heapSize-1 && COST(*(cand+1)) < COST(*cand)) j++, cand++;
    if (newCost <= COST(*cand)) break;
    node->heap[(j-1)/2] = (*cand);
    j = 2*j+1;
  }
  node->heap[(j-1)/2] = newElt;
}


/*============================================================================*/
__inline__ void InsertHeap (Node *node, Arc *elt) {
  /* Inserts a new element in the heap, restoring the heap property
     in worst case time logarithmic with the heap size */

  register int child, father;
  register PtrArc *heap = node->heap;
  
  child = node->heapSize++;
  father = (child-1)>>1;
  while (child > 0 && COST(heap[father]) > COST(elt)) {
    heap[child] = heap[father];
    child  = father;
    father = (child-1)>>1;
  }
  heap[child] = elt;
}


/*============================================================================*/
Path* NextPath (Path *path) {
  /* Central routine of the Recursive Enumeration Algorithm: computes the
     next path from the initial node to the same node in which the argument
     path ends, assuming that it has not been computed before.
  */
  
  Node  *node         = NULL;
  Path  *backPath     = NULL,
        *nextBackPath = NULL;
  Arc   *prevBestArc = NULL;
  
  
#ifdef DEBUG
  assert (path != NULL);
  assert (path->nextPath == NULL);
  assert (path->lastNode != NULL);
#endif

  node = path->lastNode;
  
  backPath = path->backPath;
  if (backPath != NULL) {
    nextBackPath = backPath->nextPath;
    if (nextBackPath == NULL)
      nextBackPath = NextPath (backPath);
    
    prevBestArc = (path == node->bestPath) ? node->bestArcIn : node->heap[0];
    
    if (nextBackPath != NULL)
      prevBestArc->nextCand = nextBackPath;
    else prevBestArc->cost = INFINITY_COST;
  }
  
  if (path != node->bestPath) 
    UpdateHeap(node);
  else {
    node->heapSize = 0;
    node->listHeadSize = 0;
  }
  
  if (node->listHeadSize == 0) {
    /* Searches the two best candidates in the unsorted part of the set
       of candidates */
    register PtrArc *cand, *bestCand = NULL, *secondBestCand = NULL;
    register COST_TYPE bestCost = INFINITY_COST, secondBestCost = INFINITY_COST;
    register int numberArcs;
    for (cand = node->firstArcIn + node->numberArcsIn - 1, 
	 numberArcs = node->numberArcsIn - node->heapSize;
         numberArcs > 0; cand--, numberArcs--) {
      if (COST(*cand) < secondBestCost){
	if (COST(*cand) < bestCost) {
	  secondBestCost = bestCost;
	  secondBestCand = bestCand;
	  bestCost = COST(*cand);
	  bestCand = cand;
	}
	else {
	  secondBestCost = COST(*cand);
	  secondBestCand = cand;
	}
      }
    }
    if (bestCost != INFINITY_COST) {
      PtrArc aux = *(++cand);
      if (secondBestCand == cand) secondBestCand = bestCand;
      *cand = *bestCand;
      *bestCand = aux;
      node->listHeadSize = 1;
    }
    if (secondBestCost != INFINITY_COST) {
      PtrArc aux = *(++cand);
      *cand = *secondBestCand;
      *secondBestCand = aux;
      node->listHeadSize = 2;
    }
  }

  if (node->listHeadSize > 0) {
    if (node->heapSize == 0 || COST(node->heap[node->heapSize]) < COST(node->heap[0])) {
      InsertHeap (node, node->heap[node->heapSize]);
      node->listHeadSize--;
    }
  }

  if (node->heapSize == 0 || COST(node->heap[0]) >= INFINITY_COST) {
    path->nextPath = NULL;
  } else {
    path->nextPath = CreatePath (node, node->heap[0]->nextCand, COST(node->heap[0]));
#ifdef DEBUG
    printf ("\nNext path at node %i:\t", node->name);
    PrintPath (path->nextPath);
#endif
    
  }
  
  return (path->nextPath);
  
}


/*============================================================================*/
void Copyright () {
  printf ("\n======================================================================\n");
  printf ("HREA version %s, Copyright (C) 1999 Victor Jimenez and Andres Marzal\n",
	  VERSION);
  printf ("HREA comes with ABSOLUTELY NO WARRANTY.\n");
  printf ("This is free software, and you are welcome to redistribute it under\n");
  printf ("certain conditions; see the README and COPYING files for more details.\n");
}

/*============================================================================*/
void Help (char *program) {
  printf ("======================================================================\n");
  printf ("\nUse: %s GRAPH_FILE NUMBER_OF_PATHS [-paths] [-tdijkstra]\n", program);
  printf ("     Optional arguments:\n");
  printf ("       -paths Print the sequence of nodes for each path\n");
  printf ("       -tdijkstra Cumulate also the time of Dijkstra's algorithm\n");
  printf ("See the README file for more details.\n");
  printf ("======================================================================\n");
  exit (1);
}

/*============================================================================*/
int main (int argc, char **argv) {
 
  Graph  graph;
  Path   *path;
  int    i, numberPaths = 1;
  time_t date;
  struct tm *localDate;
  char   hostName[200] = "";
  int    showPaths = 0;
  int    measureDijkstra = 0;
  float  *cumulatedSeconds;
#ifdef DEBUG
  Node   *node;
  int    numberNodes;
#endif
  
  /****************** Prints the copyright notice  **************************/
  Copyright ();

  /************** Reads the command line parameters *************************/
  if (argc < 3) Help (argv[0]);
  numberPaths = atoi (argv[2]);
  for (i=3; i < argc; i++) {
    if (strcmp(argv[i], "-paths") == 0) showPaths = 1;
    else if (strcmp(argv[i], "-tdijkstra") == 0)  measureDijkstra = 1;
    else Help(argv[0]);
  }

  /****************** Prints experimental trace information *****************/
  gethostname (hostName, 200);
  date = time (NULL);
  localDate = localtime (&date);
  printf ("======================================================================\n");
  printf ("CommandLine: ");
  for (i = 0; i < argc; i++)
    printf (" %s", argv[i]);
  printf ("\nHostname: %s", hostName);
  printf ("\nDate: %s", asctime(localDate));
  printf ("======================================================================\n");

  
  /******************* Reads the graph from file ****************************/
  
  LoadGraph(&graph, argv[1]);
  
  /********** Allocates memory for time counters *****************************/
  cumulatedSeconds = malloc (sizeof(cumulatedSeconds[0])*numberPaths);
  if (cumulatedSeconds == NULL) {
    perror("Not enough memory for time counters.\n");
    exit(1);
  }
  
  /****************** Computes the shortest path tree ***********************/
  if (measureDijkstra == 1)
    ClockReset ();

  Dijkstra (&graph);

  if (measureDijkstra == 1)
    cumulatedSeconds[0] =  ClockTotal();
  else {
    cumulatedSeconds[0] =  0;
    ClockReset ();
  }

#ifdef DEBUG
  for (node = graph.node, numberNodes = graph.numberNodes; numberNodes != 0; 
       node++, numberNodes--) { 
    printf ("\nBest Path for FinalNode=%i: ", node->name);
    PrintPath (node->bestPath);
  }
#endif
  
  /******************** Computes the K shortest paths ***********************/
  i = 2;
  path = graph.finalNode->bestPath;
  while (i <= numberPaths && path != NULL) {
    path = NextPath (path);
    cumulatedSeconds[i-1] = ClockTotal();
    i++;
  }
  
  /************ Prints the computed paths and time counters ******************/
  i = 1;
  path = graph.finalNode->bestPath;
  while (i <= numberPaths && path != NULL && path->cost < INFINITY_COST) {
    printf ("\nN=%i:\t", i);
    if (showPaths == 1) PrintPath (path);
    printf (" \t(CumulatedSeconds: %.2f)", (float) cumulatedSeconds[i-1]);
    path = path->nextPath;
    i++;
  }
  printf ("\nTotalExecutionTime: %.2f\n", (float) cumulatedSeconds[i-2]);
  return (0);
  
}
