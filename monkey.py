import os
import shutil
from tqdm import tqdm

class Error(OSError):
	pass
	
def copy2(src, dst, *, follow_symlinks=True):
	"""Copy data and all stat info ("cp -p src dst"). Return the file's
	destination."

	The destination may be a directory.

	If follow_symlinks is false, symlinks won't be followed. This
	resembles GNU's "cp -P src dst".

	"""
	if os.path.isdir(dst):
		dst = os.path.join(dst, os.path.basename(src))
	copyfile(src, dst, follow_symlinks=follow_symlinks)
	shutil.copystat(src, dst, follow_symlinks=follow_symlinks)
	return dst
	
def copytree(src, dst, symlinks=False, ignore=None, copy_function=copy2,
			 ignore_dangling_symlinks=False):
	
	names = os.listdir(src)
	if ignore is not None:
		ignored_names = ignore(src, names)
	else:
		ignored_names = set()

	os.makedirs(dst)
	errors = []
	for name in names:
		if name in ignored_names:
			continue
		srcname = os.path.join(src, name)
		dstname = os.path.join(dst, name)
		try:
			if os.path.islink(srcname):
				linkto = os.readlink(srcname)
				if symlinks:
					# We can't just leave it to `copy_function` because legacy
					# code with a custom `copy_function` may rely on copytree
					# doing the right thing.
					os.symlink(linkto, dstname)
					copystat(srcname, dstname, follow_symlinks=not symlinks)
				else:
					# ignore dangling symlink if the flag is on
					if not os.path.exists(linkto) and ignore_dangling_symlinks:
						continue
					# otherwise let the copy occurs. copy2 will raise an error
					if os.path.isdir(srcname):
						copytree(srcname, dstname, symlinks, ignore,
								 copy_function)
					else:
						copy_function(srcname, dstname)
			elif os.path.isdir(srcname):
				copytree(srcname, dstname, symlinks, ignore, copy_function)
			else:
				# Will raise a SpecialFileError for unsupported file types
				copy_function(srcname, dstname)
		# catch the Error from the recursive copytree so that we can
		# continue with other files
		except Error as err:
			errors.extend(err.args[0])
		except OSError as why:
			errors.append((srcname, dstname, str(why)))
	try:
		shutil.copystat(src, dst)
	except OSError as why:
		# Copying file access times may fail on Windows
		if getattr(why, 'winerror', None) is None:
			errors.append((src, dst, str(why)))
	if errors:
		raise Error(errors)
	return dst
	
def copyfile(src, dst, *, follow_symlinks=True):
	"""Copy data from src to dst.

	If follow_symlinks is not set and src is a symbolic link, a new
	symlink will be created instead of copying the file it points to.

	"""
	
	if shutil._samefile(src, dst):
		raise SameFileError("{!r} and {!r} are the same file".format(src, dst))

	for fn in [src, dst]:
		try:
			st = os.stat(fn)
		except OSError:
			# File most likely does not exist
			pass
		else:
			# XXX What about other special files? (sockets, devices...)
			if shutil.stat.S_ISFIFO(st.st_mode):
				raise SpecialFileError("`%s` is a named pipe" % fn)

	if not follow_symlinks and os.path.islink(src):
		os.symlink(os.readlink(src), dst)
	else:

		with open(src, 'rb') as fsrc:
			with open(dst, 'wb') as fdst:
				copyfileobj(fsrc, fdst)
	return dst

def walkdir(folder):
	"""Walk through each files in a directory"""
	for dirpath, dirs, files in os.walk(folder):
		for filename in files:
			yield os.path.abspath(os.path.join(dirpath, filename))
			
def getfoldersize(src):
	# Preprocess the total files sizes
	sizecounter = 0
	for filepath in walkdir(src):
		sizecounter += os.stat(filepath).st_size
	
	return sizecounter

def copyfileobj(fsrc, fdst, length=16*1024):
	global pbar
	while True:
		buf = fsrc.read(length)
		if buf:
			fdst.write(buf)
			#pbar.set_postfix(file=filepath[-10:], refresh=False)
			pbar.update(len(buf))
		else:
			break

def copy(src, dst, *, follow_symlinks=True):
	if os.path.isdir(dst):
		dst = os.path.join(dst, os.path.basename(src))

	sizecounter = getfoldersize(src)
	
	global pbar
	with tqdm(total=sizecounter,unit='B', unit_scale=True, unit_divisor=1024, leave = True, miniters = 1, desc = '[*] Copying') as pbar:
		copytree(src, dst)
		shutil.copymode(src, dst)
	return dst