#========================================================================
#  Makefile for HREA.c
# 
#  Use: make HREA
#
#  Authors: Victor Jimenez and Andres Marzal
#           Dept. de Informatica, Universitat Jaume I, Castellon, Spain
#           {vjimenez,amarzal}@inf.uji.es
#
#  Program HREA - Version 1.1 - July 1999
#========================================================================


# Flags for debug:
CFLAGS = -g -I. -DDEBUG

# Flags for experimentation (maximum optimization level):
CFLAGS = -O6 -Wall -I. 

OBJS = loadgraph.o dijkstra.o chronometer.o 

#========================================================================
# Main program
#========================================================================

HREA: HREA.c HREA.h $(OBJS)
	gcc HREA.c $(CFLAGS) $(OBJS) -o $@

#========================================================================
# Auxiliary modules
#========================================================================

loadgraph.o: loadgraph.c loadgraph.h HREA.h
	gcc loadgraph.c $(CFLAGS) -c -o $@

dijkstra.o: dijkstra.c dijkstra.h HREA.h
	gcc dijkstra.c $(CFLAGS) -c -o $@

chronometer.o: chronometer.c chronometer.h
	gcc chronometer.c $(CFLAGS) -c -o $@


