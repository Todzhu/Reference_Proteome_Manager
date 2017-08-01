"""
Delan Huang, 2017-07-12
"""
# Built-in module imports
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox, filedialog
import os
import sys
import ftplib
import datetime
import re
import copy
import urllib.request

# Imports dependent on other files
# This python file only uses built-in modules, no external downloads required
try:
    import fasta_lib_Py3 as fasta_lib
except ImportError:
    print("Could not import all files.")
    sys.exit()

# Global Variables
FTP_URL = 'ftp.ensembl.org'
REF_PROT_PATH = '/pub/current_fasta'
HEADERS = ["COMMON NAME", "LATIN NAME", "TAX ID", "ENSEMBL ASSEMBLY"]
BANNED = ["README", "CHECKSUMS"]

# Get HTML page from Ensembl for parsing
PARSE_URL = r'http://www.ensembl.org/info/about/species.html'
RESPONSE = urllib.request.urlopen(PARSE_URL)
DATA = RESPONSE.read()
TEXT = DATA.decode('utf-8')

# Helper Classes
class AnimalEntry:
    def __init__(self, c_n, l_n, taxid, e_a, acc, g_m, v_d, r_d, p_a):
        self.common_name = c_n          # Species Common Name
        self.latin_name = l_n           # Species Latin Name
        self.taxID = taxid              # Taxonomy ID Number
        self.ensembl_assembly = e_a     # 
        self.accession = acc            # 
        self.genebuild_method = g_m     # 
        self.variation_database = v_d   # 
        self.reg_database = r_d         # 
        self.pre_assembly = p_a         #

    # Define getter/setter methods (Can include more as necessary)
    def getCommonName(self):
        return self.common_name
    def setCommonName(self, c_n):
        self.common_name = c_n
    def getLatinName(self):
        return self.latin_name
    def setLatinName(self,l_n):
        self.latin_name = l_n
    def getTaxID(self,):
        return self.taxID
    def setTaxID(self, taxid):
        self.taxID = taxid
    def getEnsemblAssembly(self,):
        return self.ensembl_assembly
    def setEnsemblAssembly(self, e_a):
        self.ensembl_assembly = e_a

# Build GUI
class GUI:
    """Main GUI class for application."""
    def __init__(self, url, ref_prot_path, text, headers, banned_list):
        """Create object and set some state attributes."""
        self.url = url                      # url of UniProt FTP site
        self.ftp = None                     # FTP object (set in login method)
        self.text = text                    # HTML text of webpage
        self.raw_table = []                 # HTML text of just animals table
        self.selected_entries = []          # List of selected AnimalEntry objects
        self.animal_list = []               # List of all AnimalEntry objects
        self.banned_list = banned_list      # List of file identifiers to be omitted when downloading
        self.date = ""                      # This should be a UniProt version (i.e. 2017.07 for July release)        
        self.headers = headers              # Needed for columns in tables
        self.proteome_IDs = []              # List of unique proteome IDs
        
        # List of characters that cannot be in folder names
        self.illegal_characters = r"[\\#%&{}/<>*?:]"

    # Helper Class Functions
    def login(self):
        """Open an FTP connection and login."""
        self.ftp = ftplib.FTP()
        self.ftp.connect(str(self.url))
        self.ftp.login()

    def logout(self):
        """Close the FTP connection."""
        try:
            self.ftp.quit()
        except:
            pass # we will get error if there is no FTP connection to close
        
    def cleanCommonName(self, name):
        p = re.compile(r"alt=\"(.*?)\"")
        m = p.search(name)
        return m.groups()[0].replace(" ", "-")

    def cleanLatinName(self, name):
        p = re.compile(r"<i\b[^>]*>(.*?)</i>")
        m = p.search(name)
        return m.groups()[0].replace(" ", "-")

    def createRawTable(self):
        # Setup html file to find required information 
        # find start and end of h3 header block
        TEXT = self.text
        if "<td" in TEXT:
            start_ind = TEXT.index("<td")
        if "</table>" in TEXT:
           end_ind = TEXT.index("</table>")

        # Text Block that needs to be parsed
        self.raw_table = TEXT[start_ind:end_ind]

    def parseRawTable(self):
        # Parse header into animal list
        # Need an alternative path for missing entries where gene build method is "import"
        parser = re.compile(r'<td\b[^>]*>(.*?)</td>|</span\b[^>]*>(.*?)</span>')
        matched_groups = parser.findall(self.raw_table)
        parsed = []
        for i in range(0, len(matched_groups), 9):  # Split 1D list into 2D so that each animal has 9 attributes
            animal = matched_groups[i:i+9]
            parsed.append(animal)
            
        # We want to remove the empty space produced by alternative path
        for animal in parsed:
            for i in range(len(animal)):
                for path in animal[i]:
                    if path:
                        animal[i] = path
            common_name = self.cleanCommonName(animal[0])
            latin_name = self.cleanLatinName(animal[1])
            tax_id = animal[2]
            if not str(tax_id).isdigit():  # In case tax_id is something other than a number
                tax_id = "000"
            
            animal_obj = AnimalEntry(common_name, latin_name, tax_id, animal[3], animal[4],
                                     animal[5], animal[6], animal[7], animal[8])
            self.animal_list.append(animal_obj)


    # TODO: Species name search is working, but taxID is not
    def filterEntries(self):
        """ FIX DESC: Checks values search fields, filters all proteome IDs associated with
        selected kingdoms, taxon numbers, and/or species names, then returns a list with all matching entries.
        """
        # get the species and taxonomy substring filters
        species_entry = self.searchSpecies.get().lower()
        tax_entry = self.searchTax.get()        

        # filter on taxonomy number substring
        self.selected_entries = [entry for entry in self.animal_list if tax_entry in entry.getTaxID()]

        # filter on species name substring
        self.selected_entries = [entry for entry in self.animal_list
                                 if species_entry in entry.getCommonName().lower()
                                 or species_entry in entry.getLatinName().lower()]
        
    # TODO
    def get_filtered_proteome_list(self):
        """ Calls relevant methods to create filtered lists, then finds intersection of the lists, 
        and outputs relevant info to user
        """
        self.filterEntries()        

        if len(self.selected_entries) == 0:
            # Ask if user wants all entries shown if no filters are selected
            answer = messagebox.askyesno("Are you sure?",
                                         "No filters were selected and/or found. Would you like to show all databases?")
            if answer:
                self.selected_entries = self.animal_list
            else:
                return None
                    
        # Only show relevant info to user in entries
        entries = [[entry.getCommonName(), entry.getLatinName(),
                    entry.getTaxID(), entry.getEnsemblAssembly()]
                    for entry in self.selected_entries]

        # clear entries before importing
        for row in self.tree_left.get_children():
            self.tree_left.delete(row)
        for entry in sorted(entries):
            self.tree_left.insert('', 'end', values=entry)

        self.status_bar.config(text=("List updated with %s entries" % len(self.selected_entries)))
        
    def reset_filters(self):
        """Resets filters to defaults."""
        self.searchSpecies.delete(0, END)
        self.searchTax.delete(0, END)
        
    def sort_text_column(self, tv, col, reverse=False):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        l.sort(key=lambda x: x[0].lower(), reverse=reverse)

        # rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        # reverse sort next time
        tv.heading(col, command=lambda col_=col: self.sort_text_column(tv, col_, not reverse))
    
    def sort_num_column(self, tv, col, reverse=False):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        l.sort(key=lambda x: int(x[0]), reverse=reverse)

        # rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        # reverse sort next time
        tv.heading(col, command=lambda col_=col: self.sort_num_column(tv, col_, not reverse))
    
    def move_to_left(self):
        selection = self.tree_right.selection()  # creates sets with elements "I001", etc.
        
        for selected in selection:
            selected_copy = self.tree_right.item(selected)  # creates a set of dicts
            self.tree_right.delete(selected)
            self.tree_left.insert('', 'end', values=selected_copy['values'])
        self.status_bar.config(text="{} dropped".format(selected_copy['values'][-1]))

    def move_to_right(self):
        selection = self.tree_left.selection()  
        
        for selected in selection:
            selected_copy = self.tree_left.item(selected)
            self.tree_left.delete(selected)
            self.tree_right.insert('', 'end', values=selected_copy['values'])
        self.status_bar.config(text="{} added".format(selected_copy['values'][-1]))  # Species name should be last

    def normalizeString(self, string_name, remove_chars, dash=True):
        """ This function will remove any characters found in the remove chars list from the
            target string.
        """
        for char in remove_chars:
            string_name = string_name.replace(char, "")
        if dash:
            string_name = string_name.replace(" ", "-")

        string_name = string_name.strip()
        return string_name

    def save_to_defaults(self):
        answer = True
        # Throw a warning to overwrite
        if os.path.isfile("defaults_Ensembl.txt"):
            answer = messagebox.askyesno("File Detected!",
                                         "A defaults_Ensembl.txt file was already found. Would you like to overwrite?")
        if answer:
            save_path = filedialog.askdirectory()
            try:
                os.chdir(save_path)

                items = self.tree_right.get_children()
                databases = [self.tree_right.item(item)['values'] for item in items]               

                with open("defaults_Ensembl.txt", "w") as defaults_txt:
                    for database in databases:
                        defaults_txt.write("{}\n".format(database))

                self.status_bar.config(text="Databases saved to defaults_Ensembl.txt")
            except OSError:
                messagebox.showwarning("Invalid Filename!", "Cannot save defaults_Ensembl.txt to selected folder!")
                return None
        else:
            return None

    def import_defaults(self, initial=False):
        try:
            if initial:
                with open("defaults_Ensembl.txt", "r") as defaults_txt:
                    databases = defaults_txt.readlines()
                self.status_bar.config(text="defaults_Ensembl.txt imported.")
            else:
                import_root = filedialog.askopenfilename().rsplit("/", 1)[0] + "/"
                os.chdir(import_root)

                with open("defaults_Ensembl.txt", "r") as defaults_txt:
                    databases = defaults_txt.readlines()
                self.status_bar.config(text="defaults_Ensembl.txt imported.")
        except FileNotFoundError:
            self.status_bar.config(text="No defaults imported/defaults could not be found")
            return None
        except OSError:
            messagebox.showwarning("Invalid File!", "Invalid file selection!")

        
        # Clear selected databases before importing
        for row in self.tree_right.get_children():
                self.tree_right.delete(row)

        remove_characters = r"[],\'"  
        for database in databases:
            # make a new zombie list to parse kingdom from species name
            database = self.normalizeString(database, remove_characters, False)
            common_name = database.split()[0]
            lastin_name = database.split()[1]
            tax_id = database.split()[2]
            ens_assembly = database.split()[3]
            # maybe look into parsing the database entry in defaults using a regex (to preserve internal brackets)

            clean_database = [common_name, lastin_name, tax_id, ens_assembly]
            self.tree_right.insert('', 'end', values=clean_database)
            
    """TODO: This function """        
    def download_databases(self):
        """Fetches the database files for the selected species."""
        self.login()    # refresh the FTP connection
        
        # throw warning if no databases selected
        if len(self.tree_right.get_children()) == 0:
               messagebox.showwarning("Empty Selection", "No databases were selected for download!")
               return None  # exit function
            
        # get parent folder location for database download
        db_default = os.getcwd()
        abs_path = filedialog.askdirectory(parent=self.root, initialdir=db_default,
                                           title='Select container for Ensembl downloads')
        if not abs_path:
            return None

        # Make a separate folder to contain all files
        ensembl_dir_name = r"ensembl_{}".format(self.date)
        uniprot_dir_path = os.path.join(abs_path, uniprot_dir_name)
        try:
            os.mkdir(uniprot_dir_path)
        except FileExistsError:
            pass
        os.chdir(uniprot_dir_path)

        # convert taxonomy IDs back to proteome IDs
        tax_id_list = [self.tree_right.item(entry)['values'][0] for entry in self.tree_right.get_children()]
        set_tax_id_list = list(set(tax_id_list))  # remove duplicates (if any)
        if len(tax_id_list) != len(set_tax_id_list):
            messagebox.showwarning("Duplicates found!", "Duplicate databases were selected and will be ignored!")

        download_entries = [entry for entry in self.animal_list if int(entry.tax_ID) in set_tax_id_list]

        # add normalized folder name attribute
        [entry.makeFolderName(self.date) for entry in download_entries]

        for entry in download_entries:
            # move to the FTP site branch where files are located
            self.ftp.cwd(entry.ftp_file_path)
            
            # set local location for the download
            try:
                os.mkdir(os.path.join(uniprot_dir_path, entry.download_folder_name))
                os.chdir(os.path.join(uniprot_dir_path, entry.download_folder_name))
            except FileExistsError:
                os.chdir(os.path.join(uniprot_dir_path, entry.download_folder_name))
            except OSError:
                print("OSError")
                print('Download for this entry failed:')
                entry.snoop()
                continue
            
            for file in entry.ftp_download_list:
                # skip any files that we do not want to download                    
                if self.banned_file(file):
                    continue
                
                # download the file (skip if already dowloaded)
                if os.path.exists(os.path.join(uniprot_dir_path, entry.download_folder_name, file)):
                    continue
                self.status_bar.config(text="Downloading {} file".format(file))
                self.root.update_idletasks()
                self.ftp.retrbinary('RETR {}'.format(file), open('{}'.format(file), 'wb').write)
                print("{} is done downloading".format(file))

            """Discontinued for now"""
            # self.combine_fasta_files(uniprot_dir_path, entry)

        messagebox.showinfo("All Downloads Completed!", "Downloads Finished!")

        # reset right tree_view and associated lists
        for row in self.tree_right.get_children():
            self.tree_right.delete(row)

    def banned_file(self, fname):
        """False if fname in banned list."""
        skip = False
        for ban in BANNED:
            if ban.lower() in fname.lower():
                skip = True
        return skip

    def combine_fasta_files(self, uniprot_dir_path, entry):
        """Combines fasta and additional fasta files and decompresses."""
        # get the list of protein fasta files
        temp_files = [x for x in entry.ftp_download_list if 'fasta' in x.lower()]
        fasta_files = []
        for f in temp_files:
            if not self.banned_file(f):
                fasta_files.append(f)
        fasta_files.sort()

        # create the new file name and open file
        new_fasta_file = fasta_files[0].replace('.fasta.gz', '')
        new_fasta_file = new_fasta_file + '_' + entry.short_name + '_all.fasta'
        fasta_out_obj = open(os.path.join(uniprot_dir_path, new_fasta_file), 'w')

        # set up to read the fasta file entries and init counters
        sp_count = 0
        iso_count = 0
        tr_count = 0
        p_count = 0
        p = fasta_lib.Protein()

        # Get radiobutton value
        rbtn_value = self.rbtn_var.get()

        # read entries and write to new file
        for fasta in fasta_files:
            f = fasta_lib.FastaReader(os.path.join(uniprot_dir_path, entry.download_folder_name, fasta))
            while f.readNextProtein(p, False):
                """PW
                Need to think about what to count and report.
                Need radio buttons for canonical or canonical+isoforms as desired databases.
                Probably need another method to process and analyze canonical only option.
                The FTP databases may not be something that one can get via web downloads (and vise versa).
                It is not clear if documentation at UniProt accurately describes reference proteomes.
                """
                p_count += 1
                if p.accession.startswith('sp|'):
                    sp_count += 1
                if p.accession.startswith('tr|'):
                    tr_count += 1
                if ('-' in p.accession) or ('isoform' in p.description.lower()):
                    if rbtn_value == 0:  # only download canonical sequences
                        continue
                    iso_count += 1
                p.printProtein(fasta_out_obj)

        # close new file
        fasta_out_obj.close()

        # print stats
        print('proteome:', entry.proteome_ID, 'species:', entry.species_name)
        print('tot_count:', p_count, 'sp count:', sp_count, 'tr count:', tr_count, 'isoform count:', iso_count)
           
    def quit_gui(self):
        """Quits the GUI application."""
        self.logout()   # close the FTP connection
        self.root.withdraw()
        self.root.update_idletasks()
        self.root.destroy()
        sys.exit()


    # Main Create GUI Function
    def create_gui(self):
        """Creates the main GUI window and starts the event loop."""
        self.root = Tk()
        self.root.title("Ensembl Reference Proteome Downloader")
        self.root.geometry("1250x700+250+150")
        self.root.minsize(1250, 650)

        # Check boxes and Import button Frame
        ## Main Frame
        optionFrame = LabelFrame(self.root, text="Options")
        optionFrame.pack(side=TOP, padx=5, pady=5)

        # Search Window
        ## Main Frame
        searchWindowFrame = LabelFrame(optionFrame, text="Filters")
        searchWindowFrame.pack(side=BOTTOM, fill=BOTH, expand=YES, padx=5, pady=5)

        # Create search bars/buttons
        species_frame = Frame(searchWindowFrame)
        species_frame.pack(fill=X, padx=5, pady=5)
        species_label = Label(species_frame, text="Species Name:")
        species_label.pack(side=LEFT, padx=5, pady=5)
        self.searchSpecies = Entry(species_frame)
        self.searchSpecies.pack(side=RIGHT, fill=X, expand=YES, padx=5, pady=5)        

        tax_frame = Frame(searchWindowFrame)
        tax_frame.pack(fill=X, padx=5, pady=5)
        tax_label = Label(tax_frame, text="Taxonomy ID:")
        tax_label.pack(side=LEFT, padx=5, pady=5)
        self.searchTax = Entry(tax_frame)
        self.searchTax.pack(side=RIGHT, fill=X, expand=YES, padx=5, pady=5)       

        ## Show filtered list button and reset filters button
        filter_button = Button(searchWindowFrame, text="Show Filtered List", command=self.get_filtered_proteome_list)
        filter_button.pack(side=LEFT, padx=10, pady=10)
        clear_button = Button(searchWindowFrame, text="Reset Filters", command=self.reset_filters)
        clear_button.pack(side=RIGHT, padx=10, pady=10)

        # Entry mover-thingy Frame
        ## Main Frame
        entryFrame = LabelFrame(self.root, text="Entries")
        entryFrame.pack(side=TOP, fill=BOTH, expand=YES, padx=5, pady=5)

        ## Left Window
        leftWindowFrame = LabelFrame(entryFrame, text="Reference Proteomes")
        leftWindowFrame.pack(fill=BOTH, expand=YES, side=LEFT, padx=5, pady=10)

        # Create TreeView
        self.tree_left = Treeview(leftWindowFrame, columns=self.headers, show="headings")
        self.tree_left.pack(fill=BOTH, expand=YES, side=LEFT, padx=5, pady=5)
        for col in self.headers:
            if col in ["TAX ID"]:
                self.tree_left.heading(col, text=col.title(),
                                       command=lambda col_=col: self.sort_num_column(self.tree_left, col_))
                self.tree_left.column(col, minwidth=25, width=100, stretch=NO, anchor=E)
            else:
                self.tree_left.heading(col, text=col.title(), anchor=W,
                                       command=lambda col_=col: self.sort_text_column(self.tree_left, col_))
                self.tree_left.column(col, minwidth=25, width=150, stretch=NO)
        """Reconfigure this later"""
        # self.tree_left.column(self.headers[-1], minwidth=25, width=650, stretch=YES)  # assumes species name is always last

    
        # Add scrollbars to the TreeView 
        leftScrollY = Scrollbar(leftWindowFrame, orient=VERTICAL)
        leftScrollY.pack(side=RIGHT, fill=Y)
        
        leftScrollX = Scrollbar(self.tree_left, orient=HORIZONTAL)
        leftScrollX.pack(side=BOTTOM, fill=X)    

        self.tree_left.config(yscrollcommand=leftScrollY.set, xscrollcommand=leftScrollX.set)
        leftScrollY.config(command = self.tree_left.yview)
        leftScrollX.config(command = self.tree_left.xview)
        
        
        ## Menu Buttons
        buttonFrame = Frame(entryFrame)
        buttonFrame.pack(side=LEFT)

        addButton = Button(buttonFrame, text="Add Proteome(s)", command=self.move_to_right)
        addButton.pack()
        addButton.config(width=15)

        removeButton = Button(buttonFrame, text="Drop Proteome(s)", command=self.move_to_left)
        removeButton.pack()
        removeButton.config(width=15)
        
        saveButton = Button(buttonFrame, text="Save Defaults", command=self.save_to_defaults)  
        saveButton.pack()
        saveButton.config(width=15)

        importButton = Button(buttonFrame, text="Import Defaults", command=self.import_defaults)
        importButton.pack()
        importButton.config(width=15)
        

        ## Right Window
        rightWindowFrame = LabelFrame(entryFrame, text="Selected Proteomes")
        rightWindowFrame.pack(fill=BOTH, expand=YES, side=RIGHT, padx=5, pady=10)
        
        self.tree_right = Treeview(rightWindowFrame, columns=self.headers, show="headings")
        self.tree_right.pack(fill=BOTH, expand=YES, side=LEFT, padx=5, pady=5)
        for col in self.headers:
            if col in ["TAX ID"]:
                self.tree_right.heading(col, text=col.title(),
                                       command=lambda col_=col: self.sort_num_column(self.tree_right, col_))
                self.tree_right.column(col, minwidth=25, width=100, stretch=NO, anchor=E)
            else:
                self.tree_right.heading(col, text=col.title(), anchor=W,
                                       command=lambda col_=col: self.sort_text_column(self.tree_right, col_))
                self.tree_right.column(col, minwidth=25, width=150, stretch=NO)
        """Reconfigure this later"""
        # self.tree_right.column(self.headers[-1], width=650, stretch=YES) # assumes species names are last
        
        rightScrollX = Scrollbar(self.tree_right, orient=HORIZONTAL)
        rightScrollX.pack(side=BOTTOM, fill=X)

        rightScrollY = Scrollbar(rightWindowFrame, orient=VERTICAL)
        rightScrollY.pack(side=RIGHT, fill=Y)

        self.tree_right.config(yscrollcommand=rightScrollY.set, xscrollcommand=rightScrollX.set)
        rightScrollY.config(command = self.tree_right.yview)
        rightScrollX.config(command = self.tree_right.xview)

        
        # Miscellaneous Frame
        miscFrame = Frame(self.root)
        miscFrame.pack(side=BOTTOM, fill=X, padx=5, pady=5)

        ## Download button
        downloadButton = Button(miscFrame, text="Download Databases", command=self.download_databases)
        downloadButton.pack(padx=5, pady=5)

        # Quit button
        quitButton = Button(miscFrame, text="Quit", command=self.quit_gui)
        quitButton.pack(padx=5, pady=5)

        # Status Bar
        status_frame = LabelFrame(miscFrame, text="Status")
        status_frame.pack(side=TOP, fill=X, padx=5, pady=5)
        self.status_bar = Label(status_frame, text="", relief=SUNKEN)
        self.status_bar.pack(fill=X, padx=5, pady=5)
        
        # open the FTP connection
        self.login()
        self.createRawTable()
        self.parseRawTable()  # Create Entry objects
        self.import_defaults(True)  # initial import of defaults
        self.root.protocol("WM_DELETE_WINDOW", self.quit_gui)  # Override window close event
        self.root.mainloop()

# Main Function
gui = GUI(FTP_URL, REF_PROT_PATH, TEXT, HEADERS, BANNED)
gui.create_gui()