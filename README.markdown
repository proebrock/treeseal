dtint - Directory tree integrity checking
=========================================

Summary
-------

Dtint is a tool for checking the integrity of a data structure by keeping
checksums and meta information for each file in a separate database.

Introduction
------------

Everybody saves growing amounts of data on different media. The data of often
quite valuable data like pictures from your last holidays (personal value) or
the source code of your company (monetary value). Of course we keep backups
(at least we should). We can take a backup medium, can browse the filesystem,
open a couple of files or do a fsck run. This just says the data can be read
from the disk but we do not know if the data is still intact. Maybe the medium
or filesystem uses some checksum somewhere but I am a suspicous person, I want
to know. I want to have some checksum per file saved somewhere to guarantee the
integrity of the data. Same applies of you have to suspect someone changed
data willingly which is often the case in security scenarios.

Of course I am not the first person with that idea. There are a couple of
solutions out there. You could put your backup into one or multiple archives
using your favorite compression tool. Archives keep checksums. But that would
be inconvenient when often accessing single file from that backup. There is a
tool like the md5sum tool from the
[GNU core utilities](http://www.gnu.org/software/coreutils/) or some similar
tool (with support for regression) creating MD5SUMS files in every directory.
But you end up having maybe thousands of MD5SUMS files in every directory and
the MD5SUMS file keeps just filename and checksum, not more information. Best
solution is definitely using a filesystem supporting checksums, like
[Btrfs](http://en.wikipedia.org/wiki/Btrfs) but if that is not available or
suitable, you have to look for something else.

Collection of links to similar tools or techniques:

* [shatag](https://bitbucket.org/maugier/shatag)
* [fswatch](http://fswatch.sourceforge.net/)
* [Enhancing File System Integrity Through Checksums ](http://www.filesystems.org/docs/nc-checksum-tr/nc-checksum.html)
* Some Intrusion Detection Systems (IDE)


Features
--------

* Command line based
* Portable, supports mixed usage of systems (create DB on one OS, check on another)
* Stores all information in a single [SQLite](http://www.sqlite.org/) database
* Easy to use, one file, no compilation or installation necessary
* Readable and well documented source code


Requirements
------------

* [Python](http://www.python.org/) (2.X)
* [Graphviz](http://www.graphviz.org/) (for viewing graphs in debugging)