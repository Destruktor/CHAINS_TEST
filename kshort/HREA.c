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
#include <string.h>
#include <time.h>  
#include <unistd.h>
#include <sys/times.h>  

#ifdef DEBUG
#include <assert.h>
#endif

#include <HREA.h>
#include <loadgraph.h>
#include <dijkstra.h>
#include <chronometer.h>

#define MAX 10000
#define TEMP 20
#define MAX_DEST 20
#define MAX_K 30000
#define MAX_NODES_IN_PATH 100
#define DELTA 5000

/*============================================================================
  GLOBAL VARIABLES
  ============================================================================*/

/* For experimental purposes we avoid to use the malloc system for new paths */
/* New paths are taken from this buffer by the function CreatePath           */

#define MAX_PATHS 10000000
Path pathsBuffer[MAX_PATHS];
int  numberUsedPaths = 0;
Path *firstFreePath = pathsBuffer;

int path_array[MAX_NODES_IN_PATH];
int pindex = 0;
int kindex;
int actual_k = 0;
int NUM_DEST_NODES = 0;
int GLOBAL_K;
int totalpaths = 0;
int No_of_chains = 0;
int DV = 0;
int ETED = 0;
int ACTK[MAX_DEST];

struct path_struct
      {
        int dest;
        int route[MAX_NODES_IN_PATH];
        int delay;
        };

struct sortdelay_struct
       {
        int dest;
        int delay;
        int next;
       };
       
struct chain_component
      {
        int delay;
        int dest;
      };
      
struct chain_struct
      {
       struct chain_component comp[MAX_DEST];
       int MVC;
       };
       
   
        
struct path_struct allpaths[MAX_DEST][MAX_K];
struct sortdelay_struct sort_delay[MAX_DEST*MAX_K];
struct sortdelay_struct temp_delay[MAX_DEST*MAX_K];
struct chain_struct chain[MAX_DEST*MAX_K];

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


/*=============================================================================*/
int check_simple_path()
  {
   int i, j = 0;
   int mark = 0;
   while(j < MAX_NODES_IN_PATH)
     {
       for(i = j+1; i < MAX_NODES_IN_PATH; i++)
         {
           if(path_array[j] == path_array[i] && path_array[j] != 0)
              {
                mark = 1;
                break;
                }
            }
          j = j+1;
        }
        
      return mark;
    } 


/*============================================================================*/
void PrintPath (Path *path) {
  /* Prints the path in reverse order (with the final node first). */
  Path *backPath;
  int i =0, v;
  int check = 0;
  //int kindex = 0;
  //pindex++;
  
#ifdef DEBUG
  assert (path != NULL); 
#endif
 if (path->cost < INFINITY_COST) {
  for (backPath = path; backPath != NULL; backPath = backPath->backPath)
    {
    printf ("%i-", backPath->lastNode->name);
    path_array[i] = backPath->lastNode->name;
    i++;
    }
    
    check = check_simple_path();
    printf("-*--%d--*-",check);
    
    if(check == 0 && path->cost <= DELTA)
       {
         for(v = 0; v< MAX_NODES_IN_PATH; v++)
             {
               if(path_array[v]!=0)
                 {
                   
                   printf("%d-",path_array[v]);
                   if(v==0)
                      {
                       allpaths[pindex][kindex].dest = path_array[v];
                       allpaths[pindex][kindex].delay = path->cost;
                      }
                      
                      allpaths[pindex][kindex].route[v] = path_array[v];
                      
                  }
              }
              printf (" \t(Cost: %i)", path->cost);
              kindex++;
              actual_k++;
          }    
  printf (" \t(Cost: %i)\n", path->cost);
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


/*=============================================================================*/
void initialize_path_array()
{
  int i;
  for (i = 0; i<MAX_NODES_IN_PATH; i++)
    {
      path_array[i] = 0;
     }
 }
   

/*============================================================================*/
void myPrintPath()
{
 int i,j,m;
 printf("\n **** MY PRINT FUNCTION ****\n");
 for(i = 0; i < NUM_DEST_NODES; i++)
   {
   for(j = 0; j < ACTK[i]; j++)
    { 
     if(allpaths[i][j].dest != 0)
     {
      printf("\n Destination node : %d",allpaths[i][j].dest);
      printf("\n Delay : %d", allpaths[i][j].delay);
      printf("\n Path No : %d",j+1);
      printf("\n Path : ");
      for(m = 0; m < MAX_NODES_IN_PATH; m++)
        {
         if(allpaths[i][j].route[m] != 0)
           { 
             printf("%d-",allpaths[i][j].route[m]);
           } 
        }
     } // end if
    } // end for
  } // end for

  printf("\n");                       

}

/*===========================================================================*/
void merge(int nl, int ns, int index, int *nt)
{
  int i,cursora,cursorb,cursorc;
  
  cursora = cursorb = cursorc = 0;
  
  for(i = 0; i < ns; i++)
   {
      temp_delay[i].dest = sort_delay[i].dest;
      temp_delay[i].delay = sort_delay[i].delay;  
    }
    
    while((cursora< nl)&&(cursorb<ns))
     {
       if (allpaths[index][cursora].delay <= temp_delay[cursorb].delay)
        {
          sort_delay[cursorc].dest = allpaths[index][cursora].dest;
          sort_delay[cursorc].delay = allpaths[index][cursora].delay;
          cursora++;
          cursorc++;
         }
      else
        {
         sort_delay[cursorc].dest = temp_delay[cursorb].dest;
         sort_delay[cursorc].delay = temp_delay[cursorb].delay;
         cursorb++;
         cursorc++;
        }
     }

    while(cursora< nl)
      {
        //c[cursorc++]=a[cursora++];
        sort_delay[cursorc].dest = allpaths[index][cursora].dest;
        sort_delay[cursorc].delay = allpaths[index][cursora].delay;
        cursora++;
        cursorc++;
      }

    while(cursorb < ns)
      {      

       //c[cursorc++]=b[cursorb++];
       sort_delay[cursorc].dest = temp_delay[cursorb].dest;
       sort_delay[cursorc].delay = temp_delay[cursorb].delay;
       cursorb++;
       cursorc++;
       
      }

    *nt = cursorc;
    
    

}
/*===========================================================================*/

void mergeDelay()
{
 int nc,i,num_list;
 int m;
 int num_sort = 0;
 int total = 0;
 
 for (i = 0; i < NUM_DEST_NODES; i++)
   {
    num_list = ACTK[i];
    merge(num_list, num_sort, i, &nc);
    num_sort = nc;
    total = total + ACTK[i];
   }    
 
 
 
 
 //printf("\n Total Paths : %d\n", total);
 
 
 totalpaths = total;
 
 for(m = 0; m < total; m++)
   {
    //printf("Delay : %d -> Destination : %d\n",sort_delay[m].delay, sort_delay[m].dest);
   }
   
         
   
}

/*==========================================================================*/
void findNext()
{
  int t,c,j,m;
  
  t = totalpaths-1;
  c = sort_delay[t].dest;
  sort_delay[t].next = -1;
  
  for( j = totalpaths - 2; j >= 0; j--)
    {
      if(sort_delay[j].dest != c)
         {
           sort_delay[j].next = t;
           c = sort_delay[j].dest;
         }
         
      else
       {
         sort_delay[j].next = sort_delay[t].next;
        }
        
      t = j;

    }

  //printf("\n ************* Printing Next ***********\n");
  //for(m = 0; m < totalpaths; m++)
  // {
  //  printf("Index (%d) -- Delay : %d -> Destination : %d -----Next : %d\n",m,sort_delay[m].delay, sort_delay[m].dest, sort_delay[m].next);
  // }



}

/*===========================================================================*/
void findChain()
{
  int BestChainValue, BestChainStartPos, i, j, count,k, currentChainValue;
  
  BestChainValue = 99999;
  BestChainStartPos = 1;
  int flag[MAX_DEST];
  
  for(i = 0; i < totalpaths; i++)
  {
     // Find the valid chain starting from i
     
     for(j = 0; j < MAX_DEST; j++)
        {
          flag[j] = 0;
        }  

     count = 1;
     k = sort_delay[i].next;
     flag[sort_delay[i].dest] = 1;
     
     while((k != -1) && (count != NUM_DEST_NODES))
        {
          if(flag[sort_delay[k].dest] == 0)        
            {        
              flag[sort_delay[k].dest] = 1;
              count = count + 1;
              //printf("\n I am here and i is %d and count is %d\n",i,count);
            }
            
          if(count < NUM_DEST_NODES)
            {
              k = sort_delay[k].next;
            }
            
        } // end while
        
      if(count == NUM_DEST_NODES)
        {        
          currentChainValue = sort_delay[k].delay - sort_delay[i].delay;
          //printf("\n currentChainValue is %d and count is %d\n", currentChainValue, count);
          
          if(currentChainValue < BestChainValue)
            {
             BestChainValue = currentChainValue;
             BestChainStartPos = i;
            }
        }        
   }
   
   //printf("\n\n *** Best Chain Value is %d and Best Chain Start Position is %d\n\n", BestChainValue, BestChainStartPos);
   

}

/*===========================================================================*/

int exist_in_chain(int lindex, int kindex, int destin)
{
  int m, exist = 0;
  for (m = 0; m <= kindex; m++)
     {
       if(chain[lindex].comp[m].dest == destin)
         {
           exist = 1;
         }
      
     }
   return exist;    

}



/*===========================================================================*/

void formChain()
 {
  int i,j,l=0,k,tempdest,s,t;
  int check = 0;
  for(i = 0; i< totalpaths - NUM_DEST_NODES; i++)
   { 
     k = 0;
     chain[l].comp[k].delay = sort_delay[i].delay;
     chain[l].comp[k].dest = sort_delay[i].dest;
     
     //j = i+1;
     
     for (j = i+1; j < totalpaths; j++) 
        {
          if(k < NUM_DEST_NODES)
           {
             if(sort_delay[i].dest != sort_delay[j].dest)
               {
                tempdest = sort_delay[j].dest;
                check = exist_in_chain(l,k,tempdest);
           
               //printf("\n check is %d\n",check);
           
               if(check == 0 && sort_delay[j].delay != 0)
                  {                   
               	    chain[l].comp[k+1].delay = sort_delay[j].delay;
                    chain[l].comp[k+1].dest = sort_delay[j].dest;
                    k = k+1;
                  } // end if
                } // end if
             } // end if
           } // end for j
           
           //j++;
           
        if(j == totalpaths  && k < NUM_DEST_NODES-1 )
          {   
           l--;
           //printf("\n I am here with l--%d \n",l);
           //break;
          }        
   
        //} // end for j
        
        //if (l==9)
         //{
          //printf("\n====== j is %d and k is %d and i is %d ========\n",j,k,i);
         //}
          
           l++;
          
        
     } // end for i
  
  printf("\n l is %d\n",l);
  No_of_chains = l;
 
 //printf("\n\n ---- Printing Chains-----\n\n");
 for(s = 0; s < l ; s++)
   {
      //printf("\n Chain (%d) \n", s);
      for ( t = 0; t < NUM_DEST_NODES; t++)
         {
           if(chain[s].comp[t].dest != 0)
           {
            //printf("Delay %d -> Destination %d \n", chain[s].comp[t].delay, chain[s].comp[t].dest);
            }  
         }
    }    
     
 }
  
/*============================================================================*/
void calculateMVC()
 {
   int i,j,s,diff = 0, max = 0;
    for(s = 0; s < No_of_chains ; s++)
    {
      for ( i = 0; i < NUM_DEST_NODES-1; i++)
         {
           for (j = i+1; j <= NUM_DEST_NODES - 1; j++)
             {
               
           	if(chain[s].comp[i].dest != 0)
                  {
                   diff = chain[s].comp[j].delay - chain[s].comp[i].delay;
              
              	   if(diff > max )
                     {
                      max = diff;
                      } // end if
                   } // end if
           
              } // end for j  
         } // end for i
         
         chain[s].MVC = max;
         max = 0;
         
    } // end for s
    
    
    //printf("\n\n ^^^^ Printing MVC's ^^^^ \n\n"); 
   //for( s=0 ; s < No_of_chains; s++)
       //{
         //printf("\n MVC of chain (%d) is %d\n",s,chain[s].MVC);
       // }
    
 }
    
 
/*===========================================================================*/
void findMinMVC()
 {
  int i,j=0, minMVC,k;
  minMVC = chain[0].MVC;
  //minMVC = 10000;
  printf("\n number of chains: %d", No_of_chains);
  for (i = 0; i < No_of_chains; i++)
     {
       if(chain[i].MVC < minMVC)
         {
           minMVC = chain[i].MVC;
           j = i;
         }      
   
     }
   printf("\n The Chain with Minimum MVC is (%d) with MVC %d", j, chain[j].MVC);
   DV = chain[j].MVC;
   
   printf("\n The Delays are :\n");
   for (k = 0; k < NUM_DEST_NODES; k++)
      {
        printf("Delay : %d ---- > Destination %d\n",chain[j].comp[k].delay,chain[j].comp[k].dest);
      }
      
    printf("\n Delay : %d",chain[j].comp[NUM_DEST_NODES-1].delay);
    ETED = chain[j].comp[NUM_DEST_NODES-1].delay;  
          
      
  }

/*============================================================================*/
int main (int argc, char **argv) {
 
  Graph  graph;
  Path   *path;
  int    i, numberPaths = 1;
  //int myK, myP;
  FILE *fpt;
  float ClockTicksPerSecond;
  struct tms StartTime;
  struct tms EndTime;
  float StartTimeSeconds;
  float EndTimeSeconds;
  float tdiff = 0.0;
  int initialNodeName, finalNodeName;
  int no_of_nodes,j,v;
  char ch[20];
  char arr[TEMP][20];
  int DEST_SET[TEMP];
  //int NUM_DEST_NODES = 0;
  char *ptr;
  int linecount;
  int SOURCE = 0;
  time_t date;
  struct tm *localDate;
  char   hostName[200] = "";
  char myfile[20];
  char c;
  int    showPaths = 0;
  int    measureDijkstra = 0;
  float  *cumulatedSeconds;
  float total_time_taken = 0.00;
#ifdef DEBUG
  Node   *node;
  int    numberNodes;
#endif
  
  /****************** Prints the copyright notice  **************************/
  /* Copyright ();*/

  /************** Reads the command line parameters *************************/
  if (argc < 6) Help (argv[0]); 
  numberPaths = atoi (argv[2]);
  GLOBAL_K = numberPaths;
  for (i=3; i < argc-1; i++) {
    if (strcmp(argv[i], "-paths") == 0) showPaths = 1;
    else if (strcmp(argv[i], "-tdijkstra") == 0)  measureDijkstra = 1;
    else Help(argv[0]);
  }
  strcpy(myfile, argv[1]);
  
  c = myfile[4];
  if(c == '-')
    { 
      c = myfile[5];
     }
  


  /****************** Prints experimental trace information *****************/
  gethostname (hostName, 200);
  date = time (NULL);
  localDate = localtime (&date);
  /*
  printf ("======================================================================\n");
  printf ("CommandLine: ");
  for (i = 0; i < argc; i++)
    printf (" %s", argv[i]);
  printf ("\nHostname: %s", hostName);
  printf ("\nDate: %s", asctime(localDate));
  printf ("======================================================================\n");
  */
  
  /******************* Reads the graph from file ****************************/
  
  /* printf("\n How many nodes in the graph : ");
  scanf("%d", &no_of_nodes); */

  no_of_nodes = atoi(argv[5]);
  /*
  printf("\n No of nodes : %d\n", no_of_nodes);
  */
  //printf("\n\n Input file is %s\n\n",argv[1]);
   
   fpt = fopen(argv[1],"r");
   if(fpt == NULL)
      {
         printf("\n Error reading input file %s\n",argv[1]);
         exit(-1);
      }
   
   linecount = 0;
   while((fgets(ch,MAX,fpt)) != NULL)
      {
        linecount ++;
        ch[strlen(ch)] = '\0';
        
        if(linecount == 3)
          {
            j = 0;
      	    ptr = strtok(ch," ");
      	    while(ptr != NULL)
      	      {
      	        ptr = strtok(NULL, " ");
      	        j++;
      	        if(j == 1)
      	          {
      	           SOURCE = atoi(ptr);
                   printf("Source is: %d \n", SOURCE);
                   }
               }
            }       
        
        if(linecount == 4)
          {
      		j = 0;
      		ptr = strtok(ch," ");
      		while(ptr != NULL)
      		{
                if(j > 0)
        	    {
                    strcpy(arr[j-1],ptr);
                    DEST_SET[j-1] = atoi(arr[j-1]);
                    //printf(" ptr: %s and arr %d : %s\n", ptr, j-1, arr[j-1]);
        	    }
                ptr = strtok(NULL," ");
                j++;
     		 }// end while
            NUM_DEST_NODES = j - 1;
            //printf("\n No of Dest Nodes is %d\n", NUM_DEST_NODES);
            for(v = 0; v < NUM_DEST_NODES; v++)
      	       {
                //printf("DEST_SET: %d -> %d \n", v,DEST_SET[v]);
        	}
        	break;
    	}// end if
    	//break;
    } 
    
    fclose(fpt); 
         
         
  //exit(1); 
  
   ClockTicksPerSecond = (double) sysconf(_SC_CLK_TCK);
       
  initialNodeName = SOURCE;
  
  //times(&StartTime);
  //StartTimeSeconds = StartTime.tms_utime/ClockTicksPerSecond;
  
  for(v = 0; v < NUM_DEST_NODES; v ++)
    {	  
        finalNodeName = DEST_SET[v];  
  		
  		LoadGraph(&graph, argv[1], initialNodeName, finalNodeName);
  		
  
        /* LoadGraph(&graph, argv[1]); */
  
        /********** Allocates memory for time counters *****************************/
        cumulatedSeconds = malloc (sizeof(cumulatedSeconds[0])*numberPaths);
        if (cumulatedSeconds == NULL) {
            perror("Not enough memory for time counters.\n");
            exit(1);
        }
  
  /****************** Computes the shortest path tree ***********************/
        if (measureDijkstra == 1)
            ClockReset ();

  
        times(&StartTime);
        StartTimeSeconds = StartTime.tms_utime/ClockTicksPerSecond;
  
        Dijkstra (&graph);

        if (measureDijkstra == 1)
        {
            cumulatedSeconds[0] =  ClockTotal();
            total_time_taken = total_time_taken + cumulatedSeconds[0];
        }
        else {
            cumulatedSeconds[0] =  0;
            ClockReset ();
        }

        #ifdef DEBUG
        for (node = graph.node, numberNodes = graph.numberNodes; numberNodes != 0; 
                node++, numberNodes--) { 
            //printf ("\nBest Path for FinalNode=%i: ", node->name);
            //PrintPath (node->bestPath);
        }
        #endif
  
  /******************** Computes the K shortest paths ***********************/
        i = 2;
        path = graph.finalNode->bestPath;
        while (i <= numberPaths && path != NULL) {
            path = NextPath (path);
            cumulatedSeconds[i-1] = ClockTotal();
            /* printf("\n cumulatedSeconds is %.2f and i is %d\n",cumulatedSeconds[i-1],i); */
            total_time_taken = total_time_taken + cumulatedSeconds[i-1]; 
            i++;
        }
  
  /************ Prints the computed paths and time counters ******************/
        i = 1;
        //pindex++;
        actual_k = 0;
        kindex = 0;
        path = graph.finalNode->bestPath;
        while (i <= numberPaths && path != NULL && path->cost < INFINITY_COST) {
            //printf ("\nN=%i:\t", i);
            initialize_path_array();
            if (showPaths == 1) PrintPath (path);
            //printf (" \t(CumulatedSeconds: %.2f)", (float) cumulatedSeconds[i-1]); 
            path = path->nextPath;
            i++;
            //kindex++;
        }
        pindex++;
        ACTK[v] = actual_k;
        //printf("\n Actual K for dest %d is %d\n", DEST_SET[v], ACTK[v]);
  
  
        /* printf ("\nTotalExecutionTime: %.2f\n", (float) cumulatedSeconds[i-2]); */
        /* total_time_taken = total_time_taken + cumulatedSeconds[i-1]; */

        times(&EndTime);  
        EndTimeSeconds = EndTime.tms_utime/ClockTicksPerSecond;
        tdiff = tdiff + (EndTimeSeconds - StartTimeSeconds);


     

        free (graph.node);                                                                            
        free (graph.arc);                                                                                 
        free (graph.arcIn);                                                                            
        free (graph.arcOut);
   

   //} // end if
 
 	} // end for
 //} //end for
 
 /* printf("\n Total time taken : %.2f\n", total_time_taken); */
 //printf("\n 0.%c \t %d \t %.2f\n", c, numberPaths, total_time_taken);

  times(&StartTime);
  StartTimeSeconds = StartTime.tms_utime/ClockTicksPerSecond;


  //myPrintPath();
  //printf("\n I am here\n");
  mergeDelay();
  findNext();
  findChain();
  formChain();
  calculateMVC();
  findMinMVC();
  
  times(&EndTime);
  
  EndTimeSeconds = EndTime.tms_utime/ClockTicksPerSecond;
  tdiff = tdiff + (EndTimeSeconds - StartTimeSeconds);
  //printf("\n Execution time is %f\n", tdiff);
  //printf("\n %s  %d  %d  %f\n", argv[1], DV, ETED, tdiff);
  //printf("\n ***************************************\n");
  return (0);
  
}
