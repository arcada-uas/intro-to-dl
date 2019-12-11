#!/bin/bash
#SBATCH -A project_2002238 -N 1 -n 2
#SBATCH -c 20 -p gpu --gres=gpu:v100:2 -t 1:00:00 --mem=64G
#SBATCH --reservation dlintro

module load tensorflow/2.0.0-hvd
module list

export DATADIR=/scratch/project_2002238/data

set -xv
srun python3.7 $*

