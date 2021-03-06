#!/usr/bin/env python
"""
Read large pcap or pcapng files are slow.
This code creates a csv file as a buffer to
store the data retried from pcap or pcapng
files. Instead of reading from pcap or pcapng
file each time, data will be retried from
the csv file if possible.

Delete the csv file if there is any problem.

scapy only supports pcap file.
System call of tshark is used instead.

Requires tshark.

Usage example:
data=read_pcap_files(files, columns, filter_str, output_file)
"""
import subprocess
import os
import glob
import csv

class Pcap_File_Reader:
    """
    Used to get data from buffered file, or the original pcap(ng) file.
    Usage example:
    reader=Pcap_File_Reader('pcap_file_path')
    data=reader.read_pcap(['time_delta_displayed'],'ip.src!=127.0.0.1')
    """
    def __init__(self, file_path):
        self.pcap_file_path = os.path.abspath(file_path)
        self.dirname = os.path.dirname(file_path)
        self.basename = os.path.basename(file_path)
        self.name_without_ext = os.path.splitext(self.basename)[0]
        self.csv_file_path = os.path.join(self.dirname, self.name_without_ext + '.csv')
        
    def _read_from_pcap(self, columns, filter_str):
        syscmd = 'tshark -r \'' + str(self.pcap_file_path) + '\' -Y \'' + str(filter_str) + '\' -T fields'
        for data_name in columns:
            syscmd = syscmd + ' -e \'' + str(data_name) + '\''
        print syscmd
        process = subprocess.Popen(syscmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        data = out.splitlines()
        i = 0
        for line in data:
            data[i] = line.split()
            i += 1
        return data

    def _create_csv(self,columns,filter_str):
        print 'Read from pcap(ng) file.'
        data = self._read_from_pcap(columns, filter_str)
        print 'Create buffer file.'
        with open(self.csv_file_path, 'wb') as csvoutput:
            writer = csv.writer(csvoutput, lineterminator='\n')
            all = []
            all.append(columns)
            all+=data
            writer.writerows(all)
        return data

    def _attach_columns_to_csv(self,columns,filter_str):
        print 'here'
        old_data = []                   # A list to store old csv
        all = []                        # A list to hold everything write back to csv
        with open(self.csv_file_path, 'rb') as csvinput:
            reader = csv.reader(csvinput)
            for row in reader:
                old_data.append(row)
        with open(self.csv_file_path, 'wb') as csvoutput:
            writer = csv.writer(csvoutput, lineterminator='\n')
            row0=old_data.pop(0)        # Read from existing csv file and get the header
            new_columns=[]              # Columns that doesn't exist in csv file
            columns_dict={}             # Create an index for the return data
            for column in columns:      # Check which columns that are not exist in csv file
                if column not in row0:
                    new_columns.append(column)
                    row0.append(column)
                columns_dict[column]=row0.index(column)
            print 'Read from pcap(ng) file.'
            data = self._read_from_pcap(new_columns, filter_str)
            print 'Add new column to buffer file.'
            all.append(row0)            # Attach the head line
            for i, row in enumerate(old_data):
                row+=data[i]            # Read each line from csv, attach data
                all.append(row)         # Attach new line
                data[i]=[row[columns_dict[column]] for column in columns ]# Replace data[i] with output data according to 'columns'
            writer.writerows(all)
        return data

    def read_pcap(self, columns,
                filter_str):            # e.g. read_pcap(['time_delta_displayed'],'ip.src==192.168.0.196&&ip.dst==192.64.172.182')
        try:
            with open(self.csv_file_path, 'rb') as csvinput:
                reader = csv.reader(csvinput)
                row0 = reader.next()
                columns_dict = {}       # Create an index for the return data
                for column in columns:  # Check which columns that are not exist in csv file
                    if column in row0:
                        columns_dict[column]=row0.index(column)
                    else:
                        data=self._attach_columns_to_csv(columns,filter_str)
                        return data
                data=[]
                print 'Read from buffer file.'
                for row in reader:
                    data.append([row[columns_dict[column]] for column in columns])
            return data
        except:
            #print 'No buffer file found.'
            data=self._create_csv(columns, filter_str)
            return data

def read_pcap_files(files, columns, filter_str, output_file):
    """
    This function use regex as input to process a bunch of pcap(ng) files.
    Output from each file will be combined and stored in the output file.
    Example:
    data=read_pcap_files(files, columns, filter_str, output_file)

    :param files: String. Files using regex. E.g. '*.pcap*'
    :param columns: List of strings. A list of column names, e.g. ['frame.time_delta_displayed', 'frame.len']
    :param filter_str: String. Display filter. Use Wireshark or tshark display filter rules. E.g. '!(ip.dst==127.0.0.1)' For references: https://www.wireshark.org/docs/dfref/f/frame.html
    :param output_file: String. File path to store output data. E.g. 'a.txt'
    :return: List of string
    """
    pcap_files = glob.glob(files)
    data = []                # A list to hold everything write back to csv
    with open(output_file, 'wb') as myfile:
        myfile.write('')
    for pcap_file in pcap_files:
        print 'Read data from \''+str(pcap_file)+'\''
        temp_pcap_file_reader = Pcap_File_Reader(pcap_file)
        temp_array = temp_pcap_file_reader.read_pcap(columns, filter_str)
        data += temp_array
        with open(output_file, 'ab') as myfile:
            myfile.write('\n'.join('\t'.join(line) for line in temp_array))
            myfile.write('\n')
    print 'Data stored in file \''+str(output_file)+'\''
    return data

