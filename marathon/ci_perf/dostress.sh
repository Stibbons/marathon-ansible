# -l/bin/bash
#python marathon.py master 1
#sleep 300
for masters in 2 1 3 4
do
python stressmarathon.py -f 1 1 $masters restart 1 1 || exit
for sleeptime in 0
do
for numlines in 40000 10000 100
do
for workers in 201 11 51 101 291 1
do
python stressmarathon.py 300 $workers $masters pypy $numlines $sleeptime || exit
done
done
done
done
