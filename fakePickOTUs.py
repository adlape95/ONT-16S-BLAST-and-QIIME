"""
Script for generating a fake OTU table to be used in QIIME.

Each OTU will be constituted by a single sequence, so each
individual sequence will be used for taxonomic assignment.

Input: combined_seqs.fna (see main pipeline)

Output: stdout (use '>' to redirect the output to a file)
"""
import sys

file = open(sys.argv[1]) # file combined seqs

n = 0
for line in file:
        line = line.strip()
        if line[0] == ">": # Only want header's info.
                print("denovo" + str(n) + '\t' + line.split(' ')[0][1:])
        n += 1

file.close()
