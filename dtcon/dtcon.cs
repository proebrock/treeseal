using System;
using System.Reflection;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using System.Security.Cryptography;

namespace DirTreeConsistency
{
	/// <summary>
	/// log entry class
	/// </summary>
	class LogEntry
	{
		/// <summary>
		/// time of log entry
		/// </summary>
		private DateTime time;
		/// <summary>
		/// log entry type definition
		/// </summary>
		public enum LogType { Notice = 0, Warning, Error };
		/// <summary>
		/// log entry type
		/// </summary>
		private LogType type;
		/// <summary>
		/// path of directory or file associated with message
		/// </summary>
		private string path;
		/// <summary>
		/// log message
		/// </summary>
		private string message;
		
		public LogEntry(LogType type, string path, string message)
		{
			time = DateTime.Now;		
			this.type = type;
			this.path = path;
			this.message = message;
		}
		
		public override string ToString()
		{
			string result = time.ToString("yyyy-MM-dd HH:mm:ss")
				+ "\t<" + type.ToString() + ">"
				+ "\t" + message;
			if (path.Length != 0)
				result += "\t" + path;
			return result;
		}

		public int CompareTo(LogEntry le)
		{
			if (type.Equals(le.type))
				return time.CompareTo(le.time);
			else
				return type.CompareTo(le.type);
		}
		
		public LogType Type
		{
			get
			{
				return type;
			}
		}
	}
	
	class ChecksumList
	{
		/// <summary>
		/// log entry list
		/// </summary>
		private List<LogEntry> logEntries;
		
		public List<LogEntry> LogEntries
		{
			get
			{
				return logEntries;
			}
		}		

		/// <summary>
		/// directory name of associated directory
		/// </summary>
		string dirname;
		
		// checksum configuration
		enum CrcMethods { MD5, SHA1 };
		private const CrcMethods checksumMethod = CrcMethods.MD5;
		private const string checksumFilename = "MD5SUMS";
		private const int checksumBytes = 16;
		
		/// <summary>
		/// incoming list of checksum entries from checksum file
		/// </summary>
		private Dictionary<string,byte[]> inList;
		/// <summary>
		/// outgoing list of checksum entries to be written to checksum file
		/// </summary>
		private Dictionary<string,byte[]> outList;
		
		public ChecksumList(string dirname)
		{
			this.dirname = dirname;
		}
		
		public void Check()
		{
			// reset log entries
			logEntries = new List<LogEntry>();
			// reset checksum lists
			inList = new Dictionary<string,byte[]>();
			outList = new Dictionary<string,byte[]>();
			// read checksum file
			ReadCheckSumFile();
			// go through all entries in checksum list
			foreach (KeyValuePair<string,byte[]> kvp in inList)
			{
				string path = Path.Combine(dirname, kvp.Key);
				Console.WriteLine("\t" + path + " ...");
				try
				{				
					// only for existing entries: check checksum
					if (File.Exists(path))
					{
						if (!FileChecksumOK(path, kvp.Value))
							throw new Exception("Checksum error");
						else
							logEntries.Add(new LogEntry(LogEntry.LogType.Notice, path, "File validation successful."));
					}
					else
						logEntries.Add(new LogEntry(LogEntry.LogType.Warning, path, "File referenced in checksum file not found"));
				}
				catch (Exception e)
				{
					logEntries.Add(new LogEntry(LogEntry.LogType.Error, path, e.Message));
					break;
				}
			}
			// no update of any list
		}
		
		public void Update(bool check)
		{
			// reset log entries
			logEntries = new List<LogEntry>();
			// reset checksum lists
			inList = new Dictionary<string,byte[]>();
			outList = new Dictionary<string,byte[]>();
			// read checksum file
			bool checksumFileRead = ReadCheckSumFile();
			// get path of executable
			string mypath = Assembly.GetExecutingAssembly().Location;
			// go through all files in current directory
			foreach (string file in GetFileList(dirname))
			{
				string path = Path.Combine(dirname, file);
				// skip checking current executable
				if (path == mypath)
					continue;
				Console.WriteLine("\t" + path + " ...");
				try
				{				
					// check if file in checksum list
					byte[] csum;
					if (inList.TryGetValue(file, out csum))
					{
						// transfer entry to outlist
						outList[file] = csum;
						inList.Remove(file);
						// check checksum if required by user
						if (check)
						{
							if (!FileChecksumOK(path, csum))
								throw new Exception("Checksum error");
							else
								logEntries.Add(new LogEntry(LogEntry.LogType.Notice, path, "File validation successful."));
						}
					}
					else
					{
						// determine checksum for file
						if (checksumFileRead)
							logEntries.Add(new LogEntry(LogEntry.LogType.Warning, path, "File not found in checksum file"));
						outList[file] = GetFileChecksum(path);
					}
				}
				catch (Exception e)
				{
					logEntries.Add(new LogEntry(LogEntry.LogType.Error, path, e.Message));
					break;
				}
			}
			// output warning for all files remaining in inlist
			foreach (KeyValuePair<string,byte[]> kvp in inList)
				logEntries.Add(new LogEntry(LogEntry.LogType.Warning, Path.Combine(dirname, kvp.Key),
					"File referenced in checksum file not found"));
			// write resulting checksum list list
			string checksumFile = Path.Combine(dirname, checksumFilename);
			try
			{				
				WriteChecksumList(outList, checksumFile);
			}
			catch (Exception e)
			{
				logEntries.Add(new LogEntry(LogEntry.LogType.Error, checksumFile, e.Message));
				inList.Clear();
			}
		}
		
		private bool ReadCheckSumFile()
		{
			string path = Path.Combine(dirname, checksumFilename);
			try
			{				
				if (File.Exists(path))
				{
					ReadChecksumList(inList, path);
					return true;
				}
				else
					logEntries.Add(new LogEntry(LogEntry.LogType.Warning, path, "No checksum file found"));
			}
			catch (Exception e)
			{
				logEntries.Add(new LogEntry(LogEntry.LogType.Error, path, e.Message));
			}
			return false;
		}
		
		private List<string> GetFileList(string dirname)
		{
			List<string> filelist = new List<string>();
			foreach (string s in Directory.GetFiles(dirname))
			{
				string filename = Path.GetFileName(s);
				if (!filename.Equals(checksumFilename))
					filelist.Add(filename);
			}
			filelist.Sort();
			return filelist;
		}
		
		private bool FileChecksumOK(string filename, byte[] checksum)
		{
			byte[] csum = GetFileChecksum(filename);
			if (csum.Length != checksum.Length)
				return false;
			for (int i = 0; i < csum.Length; i++)
				if (csum[i] != checksum[i])
					return false;
			return true;
		}
		
		private byte[] GetFileChecksum(string filename)
		{
			FileStream file = new FileStream(filename, FileMode.Open);
			switch (checksumMethod)
			{
				case CrcMethods.MD5:
					MD5 md5 = new MD5CryptoServiceProvider();
					return md5.ComputeHash(file);
				case CrcMethods.SHA1:
					SHA1 sha1 = new SHA1CryptoServiceProvider();
					return sha1.ComputeHash(file);
				default:
					throw new Exception("Unknown checksum method");
			}
		}
		
		private void ReadChecksumList(Dictionary<string,byte[]> list, string filename)
		{
			// read checksum file line by line
			Regex regex = new Regex(@"([A-Za-z0-9]{"
				+ (2 * checksumBytes).ToString() +
				"})[ \t]+(.+)");
			using (StreamReader sr = new StreamReader(filename))
			{
				string line;
				while ((line = sr.ReadLine()) != null)
				{
					// extract checksum and file name
					Match match = regex.Match(line);
					if (match.Length == 0)
						throw new Exception("Unmatched line in checksum file: \"" + line + "\"");
					byte[] csum = new byte[checksumBytes];
					for (int i = 0; i < checksumBytes; i++)
						csum[i] = byte.Parse(match.Groups[1].ToString().Substring(2*i, 2),
							System.Globalization.NumberStyles.HexNumber);
					list[match.Groups[2].ToString()] = csum;						
				}
			}
		}
		
		private void WriteChecksumList(Dictionary<string,byte[]> list, string filename)
		{
			// write checksum file line by line
			using (StreamWriter sw = new StreamWriter(filename, false))
				foreach (KeyValuePair<string,byte[]> kvp in list)
				{
					foreach (byte b in kvp.Value)
						sw.Write(b.ToString("x2"));
					sw.WriteLine("  " + kvp.Key);
				}
		}
	}
	
	class ChecksumTree
	{
		/// <summary>
		/// operating mode
		/// </summary>
		public enum OperatingMode
		{
			/// <summary>
			/// check only those checksums available in the checksum files, but do not update
			/// </summary>
			Check,
			/// <summary>
			/// update checksums in the checksum files by removing non-existing entries and
			/// adding new ones by determining the checksum, do not check other files
			/// </summary>
			Update,
			/// <summary>
			/// update checksums in the checksum files by removing non-existing entries and
			/// adding new ones by determining the checksum, check the other files
			/// </summary>
			CheckAndUpdate
		};
		
		/// <summary>
		/// log entry list
		/// </summary>
		private List<LogEntry> logEntries;
		
		public ChecksumTree()
		{
		}
		
		public void Execute(string dirname, OperatingMode mode)
		{
			// execute recursive dir processing
			logEntries = new List<LogEntry>();
			if (dirname.Length == 0)
				ExecuteRecurse(Directory.GetCurrentDirectory(), mode);
			else
				ExecuteRecurse(dirname, mode);
			// print summary and write log file
			int numWarn = 0;
			int numErr = 0;
			using (StreamWriter sw = new StreamWriter("dtcon.log", false))
			{
				logEntries.ForEach(delegate(LogEntry le)
				{
					switch (le.Type)
					{
						case LogEntry.LogType.Warning:
							numWarn++;
							break;
						case LogEntry.LogType.Error:
							numErr++;
							break;
					}
					sw.WriteLine(le.ToString());
				});
			}
			Console.WriteLine("All done. (" + numErr.ToString() + " errors, " +
				numWarn.ToString() + " warnings)");
			Console.ReadKey();
		}
		
		private void ExecuteRecurse(string dirname, OperatingMode mode)
		{
			// process all files in directory according to operating mode
			Console.WriteLine("Processing directory " + dirname + " ...");
			ChecksumList list = new ChecksumList(dirname);
			switch (mode)
			{
				case OperatingMode.Check:
					list.Check();
					break;
				case OperatingMode.Update:
					list.Update(false);
					break;
				case OperatingMode.CheckAndUpdate:
					list.Update(true);
					break;
				default:
					throw new Exception("Unknown operation mode");				
			}
			logEntries.AddRange(list.LogEntries);
			// process all subdirectories
			List<string> dirlist = new List<string>(Directory.GetDirectories(dirname));
			dirlist.Sort();
			foreach (string dir in dirlist)
				ExecuteRecurse(Path.Combine(dirname, dir), mode);
		}
	}
	
	class Program
	{
		static void Main()
		{
			ChecksumTree tree = new ChecksumTree();
			tree.Execute("", ChecksumTree.OperatingMode.CheckAndUpdate);
		}
	}
}
