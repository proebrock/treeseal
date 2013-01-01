TreeSeal - Directory tree integrity checking
============================================

TreeSeal is a tool for checking the integrity of a directory structure by
keeping checksums and meta information for each file in a separate database.


Introduction
------------

Everybody stashes growing amounts of files on different media. The data is
often quite valuable for us, like pictures from our last holidays (personal
value) or important personal documents (maybe monetary value). Because the
data is important we create backups (or at least we should). But how can
we check the integrity of this data? We can access the backup medium, use
the OSes filesystem check tools, browse the file system and open a couple of
files in an appropriate application. We could even copy the whole directory
tree to a different medium to check the readability of the data. But usually
there is no standard way of checking the integrity of the data itself: A
movie might be readable from the medium and to play a couple of minutes
from it might actually work, but none of this guarantees that the file has
not been damaged. Maybe the manufacturer of the medium keeps some checksums
somewhere to detect read errors, maybe the filesystem keeps checksums
somewhere. But I am a suspicous person, I want to know. I want to have some
checksum per file saved somewhere to guarantee the integrity of the data.
Same applies of you have to suspect someone changed data willingly which is
often the case in security scenarios.


Alternative Solutions
---------------------

Of course I am not the first person with that problem or with a solution.
There are a couple of solutions out there. You could put your backup into one
or multiple archives using your favorite compression tool. Archives keep
checksums. But that would be inconvenient when often accessing single file
from that backup. There is a tool like the md5sum tool from the
[GNU core utilities](http://www.gnu.org/software/coreutils/) or some similar
tool (with support for regression) creating MD5SUMS files in every directory.
But you end up having maybe thousands of extra files, one in every directory
and the MD5SUMS file keeps just filename and checksum, not more information.
Best solution is definitely using a filesystem supporting checksums, like
[Btrfs](http://en.wikipedia.org/wiki/Btrfs) but if that is not available or
suitable on your platform, you have to look for something else.

Collection of links to similar tools or techniques:

* Maybe use a distributed version control system, e.g. [Git](http://git-scm.com/)
  with an extension like [git-annex](http://git-annex.branchable.com/) or 
  [Mercurial](http://mercurial.selenic.com/) with an extension like
  [Largefiles](http://mercurial.selenic.com/wiki/LargefilesExtension)
* [shatag](https://bitbucket.org/maugier/shatag)
* [fswatch](http://fswatch.sourceforge.net/)
* [Enhancing File System Integrity Through Checksums](http://www.filesystems.org/docs/nc-checksum-tr/nc-checksum.html)
* Some Intrusion Detection Systems (IDE)


Features
--------
* Portable, supports mixed usage of systems (create DB on one OS, check on another)
* Stores all information in a single [SQLite](http://www.sqlite.org/) database
* Readable and well documented source code


Requirements
------------

* [Python](http://www.python.org/) (2.X)
* [wxPython](http://www.wxpython.org/)
* [Graphviz](http://www.graphviz.org/) (just for debugging)


