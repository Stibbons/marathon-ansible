# -l/bin/bash
#python marathon.py master 1
#sleep 300
for masters in 6 8 4
do
python stressmarathon.py -f 1 1 $masters restart 1 1 || exit
for sleeptime in 0 .01 .001
do
for numlines in 80000 40000 10000 100
do
for workers in 201 11 51 101 291
do
python stressmarathon.py 1000 $workers $masters pypy $numlines $sleeptime || exit
done
done
done
done
