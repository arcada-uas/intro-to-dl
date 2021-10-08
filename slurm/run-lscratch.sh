#!/bin/bash
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:v100:1,nvme:100
#SBATCH --time=1:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=10
#SBATCH --account=project_2005006
#SBATCH --reservation dlintro

module load tensorflow/2.6
module list

export DATADIR=$LOCAL_SCRATCH
export KERAS_HOME=/scratch/project_2005006/keras-cache
export TRANSFORMERS_CACHE=/scratch/project_2005006/transformers-cache

set -xv

tar xf /scratch/project_2005006/data/dogs-vs-cats.tar -C $LOCAL_SCRATCH

python3 $*
