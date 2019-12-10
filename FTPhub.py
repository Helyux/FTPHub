""" FTPhub is an easy ftp management tool. """

__author__ = "Lukas Mahler"
__copyright__ = "(C) 2018-2019"
__version__ = "1.4.0"
__date__ = "05.07.2019"
__email__ = "lm@ankerlab.de"
__status__ = "Prototype"

###################################################################################################
###################################################################################################

import os
import clr
import sys
import param
import monkey
import shutil
import argparse
import tempfile
import datetime
import subprocess
from tqdm import tqdm
from time import sleep
from ftplib import FTP
from getpass import getpass
from termcolor import colored


###################################################################################################
###################################################################################################


def init():
    """
    Creates a little Header with Information about the Script
    """

    header = {
        "Name": "FTPhub.py",
        "Author": __author__,
        "Copyright": __copyright__,
        "Version": __version__,
        "VDate": __date__
    }

    os.system("CLS")
    clr.cyan("######################################")
    for key in header:
        clr.cyan("{0:<5}{1:<10}{2:<2}{3:<20}#".format("#", key, ":", header[key]))
    clr.cyan("######################################")
    clr.yellow("\n[#] Loading...")
    sleep(1)


###################################################################################################

def mm_checkpwd():
    """
    Checking if we are on the Root FTP Folder
    If not, change to go there.
    """
    if status != colored("{0:12}".format("Disconnected"), "red"):
        current_path = ftp.pwd()
        # print(current_path)
        if "Dumps" in current_path:
            menu_path_index = current_path.find("/ftp")
            menu_path = current_path[:menu_path_index + 4]
            # print(menu_path)
            ftp.cwd(menu_path)


def menu():
    """
    Creates the Main Menu, we should be at the FTP Root Folder.
    Functions in this menu are prefixed mm_
    """
    mm_checkpwd()
    sleep(1)
    os.system("CLS")
    print("######################################")
    print("# {0:<35}#".format("       FTPhub - Main Menue"))
    print("# {0:<35}#".format(""))
    print("# {0:<15} {1:<12}    #".format("   Current Status:", status))
    print("# {0:<35}#".format(""))
    print("# {0:<35}#".format("Available commands:"))
    print("# {0:<35}#".format(""))
    print("# {0:<35}#".format("[ 0] Connect to Server"))
    print("# {0:<35}#".format("[ 1] Disconnect from Server"))
    print("# {0:<35}#".format("[ 2] Browse Root"))
    print("# {0:<35}#".format("[ 3] Browse Dumps"))
    print("# {0:<35}#".format("[ 4] Rotate Dumps"))
    print("# {0:<35}#".format("[ 5] Upload Dump"))
    print("# {0:<35}#".format("[ 6] Exit"))
    print("######################################")

    print("\n[*] Please select what you want to do:")
    action = input("	-> ")
    try:
        action = int(action)
    except ValueError:
        clr.red("\n[X] Wrong Input")
        return menu()
        pass
    print("")

    if action == 0:
        clr.yellow("[#] Connecting...")
        mm_connect()
    elif action == 1:
        mm_disconnect()
    elif action == 2:
        mm_browse("root")
    elif action == 3:
        mm_browse("dumps")
    elif action == 4:
        mm_rotate()
    elif action == 5:
        mm_upload()
    elif action == 6:
        ftpexit()
    else:
        clr.red("\n[X] Wrong Input")
        return menu()


def mm_connect():
    """
    Connects to a FTP-Server using the Info given in the param file
    USRN and PSWD can be None to interactively get the Info.
    THIS IS NOT SECURE and should be replaced with SFTP in the next Versions
    """

    """ monkeypatch https://stackoverflow.com/questions/44057732/connecting-to-explicit-ftp-over-tls-in-python """
    _old_makepasv = FTP.makepasv

    def _new_makepasv(self):
        host, port = _old_makepasv(self)
        host = self.sock.getpeername()[0]
        return host, port

    FTP.makepasv = _new_makepasv
    """ monkeypatch """

    global ftp
    ftp = FTP()
    ftp.connect(param.HOST, param.PORT)
    print("[*] Successfully established a Connection to [" + param.HOST + "] on PORT [" + str(param.PORT) + "]")
    if param.USRN is None:
        param.USRN = input("    Username: ")
    if param.PSWD is None:
        param.PSWD = getpass("    Password: ")
    print("[*] Trying to Authenticate as [" + param.USRN + "]")
    try:
        ftp.login(user=param.USRN, passwd=param.PSWD)
        ftp.getwelcome()
    except Exception as e:
        errorcode = e.args[0][:3]
        # print('Errorcode: {}'.format(errorcode))
        if errorcode == "530":
            clr.red("[X] Error: Wrong Login credentials ||| Errorcode: " + errorcode)
            return menu()
        else:
            clr.red("[X] Error: undefined error, check the errorcode. ||| Errorcode: " + errorcode)
            return menu()
    clr.green("[*] Successfully authenticated")

    global status
    status = colored("{0:12}".format("Connected"), "green")

    if not qu and not qd:
        return menu()


def mm_disconnect():
    """
    Disconnects you from a currently connected FTP-Server
    """
    global status
    if status != colored("{0:12}".format("Connected"), "green"):
        clr.red("[X] Not Connected to a Server")
        return menu()
    clr.yellow("[#] Disconnecting...")
    ftp.quit()
    clr.green("[*] Successfully disconnected")
    status = colored("{0:12}".format("Disconnected"), "red")
    sleep(1)
    if not qu and not qd:
        return menu()


def mm_browse(where):
    """
    Changes the Directory to the choosen, if no 'where' is defined,
    falling back to the Root FTP folder.
    """
    if status != colored("{0:12}".format("Connected"), "green"):
        clr.red("[X] Not Connected to a Server")
        return menu()
    else:
        if where == "root":
            # ftp.cwd("./")
            items = getitems()
            filemenu(items)
        elif where == "dumps":
            ftp.cwd("Dumps")
            items = getitems()
            filemenu(items)
        else:
            clr.red("[X] Path not specified, falling back to root dir")
            sleep(2)
            items = getitems()
            filemenu(items)

    return menu()


def mm_rotate():
    """
    This Checks if there are more than 15 Dumps in the Dumps Folder
    if so, deletes the oldest till there are 15 Dumps.
    """
    if status != colored("{0:12}".format("Connected"), "green"):
        clr.red("[X] Not Connected to a Server")
        return menu()
    else:
        ftp.cwd("Dumps")
        items = getitems()
        items_n = len(items)
        maxdumps = 15
        if items_n > maxdumps:
            clr.red("More than {0} Dumps! [{1}]".format(maxdumps, items_n))
            todel_n = items_n - maxdumps
            # print(items[0:todel_n])
            print("\n[*] Are you sure you want to rotate the Dumps? (Y/N)")
            inp = input("	-> ")
            print("")
            if inp == "Y" or inp == "y":
                for item in items[0:todel_n]:
                    print("[*] Deleting: {0}".format(item))
                    ftp.delete(item)
                clr.green("\n[*] Deleted the {0} oldest Dumps".format(todel_n))
                sleep(5)
            else:
                clr.red("\n[X] Aborted")
        else:
            clr.green("[*] Less then {0} Dumps [{1}]! We Gucci!".format(maxdumps, items_n))
            sleep(3)

    return menu()


def mm_upload():
    """
    Uploads a Dump Folder which lies next to the FTPhub pathwise.
    tqdm is used to show the upload progress.
    This function is based on functions wrote in savedum.py
    """
    if status != colored("{0:12}".format("Connected"), "green"):
        clr.red("[X] Not Connected to a Server")
        return menu()
    else:
        root = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
        bkp_path = createbkp(root)
        zipfile = zipbkp(bkp_path)

        filesize = os.path.getsize(zipfile)
        filename = os.path.basename(zipfile)
        ftp.cwd("Dumps")
        print("[*] Trying to transfer the Backup, please wait...")
        with open(zipfile, 'rb') as f:
            with tqdm(unit='blocks', unit_scale=True, leave=False, miniters=1, desc='[*] Uploading',
                      total=filesize) as tqdm_instance:
                ftp.storbinary('STOR ' + filename, f, 2048, callback=lambda sent: tqdm_instance.update(len(sent)))
        clr.green("[*] Successfully transfered the Backup")
        cleanup(bkp_path, zipfile)
        clr.magenta("[*] Upload-Function Successful")
        sleep(3)

        if not qu:
            return menu()


def createbkp(root):
    """
    Creates a duplicate of the Dump folder in the Temp Directory
    Throws errors when there is a Thumbs.db blocking...
    """
    temp_dir = tempfile.gettempdir()
    date = datetime.datetime.now()
    ext = date.strftime("%Y-%m-%d")
    src = root + '\\Dump'
    dst = temp_dir + '\\' + ext + "_" + "Dump"
    print("[*] Trying to create a Duplicate, please wait...")
    try:
        monkey.copy(src, dst)
    except FileExistsError:
        try:
            shutil.rmtree(dst)
        except PermissionError:
            clr.red("[X] Error: Guess there's a Thumbs.db")
    clr.green("[*] Successfully created Duplicate")
    return dst


# Reference https://stackoverflow.com/questions/45094647/encrypt-folder-or-zip-file-using-python
def zipbkp(directoryToZip):
    """
    Zips the duplicate Dumpfolder in the Temp Directory
    7zip has to be installed to use this function.
    """
    zipFileName = directoryToZip + ".zip"

    appPath = "C:\Program Files\\7-Zip"
    zApp = "7z.exe"
    zAction = 'a'
    zPass = '-p{0}'.format(param.ZIPW)
    zAnswer = '-y'
    zDir = directoryToZip
    progDir = os.path.join(appPath, zApp)

    if not os.path.isfile(progDir):
        clr.red("[X] Cannot Create .zip since 7zip is not installed!")
        sleep(3)
        return menu()

    print("[*] Trying to create .zip File, please wait...")
    cmd = [zApp, zAction, zipFileName, zPass, zAnswer, zDir]
    zipper = subprocess.Popen(cmd, executable=progDir, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    zipper.wait()
    clr.green("[*] Successfully created .zip File")
    return zipFileName


def cleanup(bkp_path, zipfile):
    """
    Cleans the Temp Directory from the Duplicate and the .zip File
    """
    print("[*] Trying to clean up, please wait...")
    try:
        shutil.rmtree(bkp_path)
        os.remove(zipfile)
    except PermissionError:
        clr.red("[X] Error: Guess there's a Thumbs.db, try to manually Clean Up the Temp Directory.")
        pass
    clr.green("[*] Successfully Cleaned")


def getitems():
    """
    Returns a list of files & directorys in the current ftp working directory
    """
    return ftp.nlst()


def filemenu(items):
    """
    Creates the File Menu, given the items of the current working Directory
    Functions in this menu are prefixed fm_
    """
    global selected
    if selected != "None":
        if is_file(selected):
            selected_show = colored("{0:20}".format(selected), "cyan")
        else:
            selected_show = colored("{0:20}".format(selected), "magenta")
    else:
        selected_show = colored("{0:20}".format(selected), "yellow")
    os.system("CLS")
    print("######################################")
    print("# {0:<35}#".format("       FTPhub - File Menue"))
    print("# {0:<35}#".format(""))
    print("# {0:<10} {1:<25}  #".format("   Selected:", selected_show))
    print("# {0:<35}#".format(""))
    print("# {0:<35}#".format("Available commands:"))
    print("# {0:<35}#".format(""))
    print("# {0:<35}#".format("[ 0] Select File/Directory"))
    print("# {0:<35}#".format("[ 1] Create Directory"))
    print("# {0:<35}#".format("[ 2] Open Directory"))
    print("# {0:<35}#".format("[ 3] Rename Selected"))
    print("# {0:<35}#".format("[ 4] Delete Selected"))
    print("# {0:<35}#".format("[ 5] Download Selected"))
    print("# {0:<35}#".format("[ 6] Upload File"))
    print("# {0:<35}#".format("[ 7] Exit to Main Menue"))
    print("# {0:<35}#".format("[ 8] Exit"))
    print("# {0:<35}#".format(""))
    print("######################################")
    print("\n# Files:")
    enumarated_items = list(enumerate(items, 1))
    for count, element in enumerate(items, 1):

        # First Check if Element is Dir or File:
        if is_file(element):
            element = colored(element, "cyan")
        else:
            element = colored(element, "magenta")

        """ HIER MUSS DIE LOGIK REIN UM EIN ROTES X STATT EINER ZAHL ANZUZEIGEN """

        if count != 0 and count % 3 == 0:
            print("[{0:>3}] {1:<31}".format(count, element))
        else:
            print("[{0:>3}] {1:<31}".format(count, element), end="")

    print("\n#")
    print("\n[*] Please select what you want to do:")
    action = input("	-> ")
    try:
        action = int(action)
    except ValueError:
        clr.red("\n[X] Wrong Input")
        return filemenu(items)
        pass
    print("")

    if action == 0:
        fm_select(enumarated_items)
    elif action == 1:
        fm_create()
    elif action == 2:
        fm_open_dir(enumarated_items)
    elif action == 3:
        fm_rename()
    elif action == 4:
        fm_delete()
    elif action == 5:
        fm_download()
    elif action == 6:
        fm_upload()
    elif action == 7:
        selected = "None"
        return menu()
    elif action == 8:
        ftpexit()
    else:
        clr.red("\n[X] Wrong Input")
        return filemenu(items)


def fm_select(enumarated_items):
    """
    Selects a File by number, given numerated Files/Directorys of a directory
    """
    global selected
    print("\n[*] Please select the File/Directory:")
    sel = int(input("	-> "))
    selected = enumarated_items[sel - 1][1]
    items = getitems()
    return filemenu(items)


def fm_create():
    """
    Creates a Directory located at the current working directory
    """
    print("\n[*] Please select the name for the directory:")
    inp = input("	-> ")
    ftp.mkd(inp)
    items = getitems()
    return filemenu(items)


def fm_open_dir(enumarated_items):
    """
    Opens a Sub-Directory by number, given numerated Files/Directorys of a directory
    after opening the Sub-Directory returning with a new filemenu
    """
    print("\n[*] Please select which directory to open:")
    sel = int(input("	-> "))
    thedir = enumarated_items[sel - 1][1]
    if is_file(thedir):
        clr.red("\n[X] Not a directory")
        sleep(2)
        items = getitems()
        return filemenu(items)
    else:
        try:
            ftp.cwd(thedir)
        except Exception as e:
            clr.red(e)
            sleep(2)
            pass
        items = getitems()
        selected = "None"
        return filemenu(items)


def fm_rename():
    """
    Renames a selected File or Directory
    """
    global selected
    print("\n[*] Please choose the new name for the selected item:")
    inp = input("	-> ")
    print(selected, inp)
    ftp.rename(selected, inp)
    selected = inp
    items = getitems()
    return filemenu(items)


def fm_delete():
    """
    Deletes a selected File or Directory using either ftp.delete or ftp.rmd
    """
    global selected
    print("\n[*] Are you sure you want to delete the selected item? (Y/N)")
    inp = input("	-> ")
    if inp == "Y" or inp == "y":
        if is_file(selected):
            ftp.delete(selected)
        else:
            ftp.rmd(selected)
        selected = "None"
        items = getitems()
        return filemenu(items)
    else:
        clr.red("\n[X] Aborted")
        sleep(1)
        items = getitems()
        return filemenu(items)


def download_handle(block, f, tqdm_instance):
    """
    Using this function on each Callback from ftp.retrbinary to update the tqdm Progressbar
    """
    f.write(block)
    tqdm_instance.update(len(block))


def fm_download(qd=False):
    """
    Downloads a File from the remote server to the current working Directory
    tqdm is used to show the download progress.
    """

    global selected
    if qd:
        ftp.cwd("Dumps")
        items = getitems()
        selected = items[-1]

    if is_file(selected):
        filesize = ftp.size(selected)
        with open(selected, 'wb') as f:
            with tqdm(unit='blocks', unit_scale=True, leave=False, miniters=1, desc='[*] Downloading',
                      total=filesize) as tqdm_instance:
                ftp.retrbinary('RETR ' + selected, lambda block: download_handle(block, f, tqdm_instance), 2048)
        clr.green("[*] Download Successful")
        sleep(2)
        items = getitems()

        if not qd:
            return filemenu(items)
    else:
        clr.red("\n[X] Can only download files")
        sleep(2)
        items = getitems()
        if not qd:
            return filemenu(items)


def fm_upload():
    """
    This is a Function to upload a file to the ftp server
    """
    print("[*] Please Input the Full Path to the File (or drag it here)")
    filepath = input("   -> ")
    if is_file(filepath):
        filesize = os.path.getsize(filepath)
        with open(filepath, 'rb') as f:
            with tqdm(unit='blocks', unit_scale=True, leave=False, miniters=1, desc='[*] Uploading',
                      total=filesize) as tqdm_instance:
                ftp.storbinary('STOR ' + os.path.basename(filepath), f, 2048,
                               callback=lambda block: tqdm_instance.update(len(block)))
        clr.green("[*] Upload Successful")
        sleep(2)
        items = getitems()
        return filemenu(items)
    else:
        clr.red("\n[X] Given Path is not a File")
        sleep(2)
        items = getitems()
        return filemenu(items)


def is_file(filename):
    """
    Determines if an ftp.nlst item is a File or a Directory
    uses a list of file endings (reference at the bottom)
    This needs to be changed as currently it's slow and unreliable
    """
    cnt = 0
    for ending in endings:
        if ending.lower() in filename.lower():
            cnt += 1
        else:
            continue
    if cnt != 0:
        return True
    else:
        return False


def ftpexit():
    """
    Exits the Hub, closing any (if existant) ftp connection
    """
    clr.yellow("[#] Exiting...")
    try:
        ftp.quit()
    except Exception as e:
        pass
    sleep(2)
    sys.exit()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-qu', action='store_true', help='Quick Upload Function')
    parser.add_argument('-qd', action='store_true', help='Quick Download Function')
    args = parser.parse_args()
    qu = args.qu
    qd = args.qd

    endings = [".zip", ".pdf", ".exe", ".txt", ".docx", ".7z", ".rar", ".py", ".xlsx", ".doc", ".xls",
               ".ppt", ".png", ".jpg", ".jpeg", ".inf", ".bin", ".reg", ".bat", ".log", ".ps1", ".bmp",
               ".ico", ".css", ".html", ".xml", ".sh", ".bak", ".ini", ".dmp", ".csv", ".sql", ".mp3",
               ".mp4", ".js", ".php", ".xls", ".pptx", ".config", ".cfg"
               ]

    root = os.path.dirname(os.path.abspath(__file__))
    status = colored("{0:12}".format("Disconnected"), "red")
    selected = colored("{0:20}".format("None"), "yellow")

    init()

    if qu:
        mm_connect()
        mm_upload()
        mm_disconnect()
        ftpexit()

    if qd:
        mm_connect()
        fm_download(qd=True)
        mm_disconnect()
        ftpexit()

    menu()

    clr.yellow("\n[#] Finished Execution, exiting...")
    sleep(2)
