linuxrun: clean linux
	./wirestub

linux: wireconst
	gcc -o wirestub wirestub.c

wireconst:
	python ../wireconst.py > wireconst.h

clean:
	rm -rf wirestub wireconst.h
