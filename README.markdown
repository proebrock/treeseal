dtint - Directory tree integrity checking
=========================================

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

* Maybe use a distributed version control system, e.g. [Git](http://git-scm.com/)
* [shatag](https://bitbucket.org/maugier/shatag)
* [fswatch](http://fswatch.sourceforge.net/)
* [Enhancing File System Integrity Through Checksums](http://www.filesystems.org/docs/nc-checksum-tr/nc-checksum.html)
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


Usage
-----
Lets say you have a directory you want to secure using dtint, lets say it is
`backup`. You create a directory somewhere else (not inside `backup`) where you
store dtint and the database. Now you are ready to create the database and
import the information:

    $ dtint.py --import backup
    Importing backup
    Importing backup/images
    Importing backup/images/dog.jpg
    Importing backup/images/child.jpg
    Importing backup/images/wife.jpg
    Importing backup/images/cat.jpg
    Importing backup/images/car.jpg
    Importing backup/letters
    Importing backup/letters/letter_to_mum.txt
    Done.

    elapsed time 140.0ms

The program will recursively traverse through the `backup` directory calculating
checksums and importing them into the database. This may take some time.
Afterwards we find some new files in our directory: `dtint.sqlite` is the
database file, `dtint.sqlite.sha256` contains a checksum over the database and
`dtint.log` collects all log outputs of the program.

To get an overview over the contents of the database, we can display its status:

    $ ./dtint.py --status
    1 root nodes in database:
      backup

    9 nodes, 3 dirs, 6 files, 23.0MB size stored in database

For more detailed information about all nodes in the database, check the
help for the `--printdb` and `--export` commands.

To check the contents of the directory against the database we do:

    $ ./dtint.py --check
    Checking backup
    Checking backup/images
    Checking backup/images/dog.jpg
    Checking backup/images/child.jpg
    Checking backup/images/wife.jpg
    Checking backup/images/cat.jpg
    Checking backup/images/car.jpg
    Checking backup/letters
    Checking backup/letters/letter_to_mum.txt
    Done.

    elapsed time 130.0ms

Lets change one file on purpose and do a check again:

    $ ls >> backup/letters/letter_to_mum.txt
    $ ./dtint.py --check
    Checking backup
    Checking backup/images
    Checking backup/images/dog.jpg
    Checking backup/images/child.jpg
    Checking backup/images/wife.jpg
    Checking backup/images/cat.jpg
    Checking backup/images/car.jpg
    Checking backup/letters
    Checking backup/letters/letter_to_mum.txt
    Error: Checksum error for backup/letters/letter_to_mum.txt,
      file size changed (77824 -> 77902),
      ctime changed (2012-04-19 12:00:40 -> 2012-04-19 12:29:45),
      atime changed (2012-04-18 11:43:21 -> 2012-04-19 12:00:58),
      mtime changed (2012-03-26 07:52:16 -> 2012-04-19 12:29:45)
    Done.

    elapsed time 130.0ms

    1 errors:
    Error: Checksum error for backup/letters/letter_to_mum.txt,
      file size changed (77824 -> 77902),
      ctime changed (2012-04-19 12:00:40 -> 2012-04-19 12:29:45),
      atime changed (2012-04-18 11:43:21 -> 2012-04-19 12:00:58),
      mtime changed (2012-03-26 07:52:16 -> 2012-04-19 12:29:45)

    Press enter ...

The program plots status messages and error messages first, in the end there
is another list of errors to have a summary.
