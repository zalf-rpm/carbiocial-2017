#!/usr/bin/python
# -*- coding: UTF-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/. */

# Authors:
# Michael Berg-Mohnicke <michael.berg@zalf.de>
# Tommaso Stella <tommaso.stella@zalf.de>
#
# Maintainers:
# Currently maintained by the authors.
#
# This file has been created at the Institute of
# Landscape Systems Analysis at the ZALF.
# Copyright (C: Leibniz Centre for Agricultural Landscape Research (ZALF)

import sys

#import json
import csv
import types
import os
from datetime import datetime, date, timedelta
from collections import defaultdict

import zmq
#print zmq.pyzmq_version()
import monica_io
import re
import numpy as np

USER = "stella"

PATHS = {
    "hampf": {
        "INCLUDE_FILE_BASE_PATH": "C:/GitHub",
        "LOCAL_PATH_TO_ARCHIV": "Z:/md/projects/carbiocial/",
        "LOCAL_PATH_TO_REPO": "C:/GitHub/carbiocial-2017/",
        "LOCAL_PATH_TO_OUTPUT_DIR": "out/"
    },

    "stella": {
        "INCLUDE_FILE_BASE_PATH": "C:/Users/stella/Documents/GitHub",
        "LOCAL_PATH_TO_ARCHIV": "Z:/projects/carbiocial/",
        "LOCAL_PATH_TO_REPO": "C:/Users/stella/Documents/GitHub/carbiocial-2017/",
        "LOCAL_PATH_TO_OUTPUT_DIR": "out/"
    },

    "berg-xps15": {
        "INCLUDE_FILE_BASE_PATH": "C:/Users/berg.ZALF-AD/GitHub",
        "LOCAL_PATH_TO_ARCHIV": "P:/carbiocial/",
        "LOCAL_PATH_TO_REPO": "C:/Users/berg.ZALF-AD/GitHub/carbiocial-2017/",
        "LOCAL_PATH_TO_OUTPUT_DIR": "out/"
    },
    "berg-lc": {
        "INCLUDE_FILE_BASE_PATH": "C:/Users/berg.ZALF-AD.000/Documents/GitHub",
        "LOCAL_PATH_TO_ARCHIV": "P:/carbiocial/",
        "LOCAL_PATH_TO_REPO": "C:/Users/berg.ZALF-AD.000/Documents/GitHub/carbiocial-2017/",
        "LOCAL_PATH_TO_OUTPUT_DIR": "G:/carbiocial-2017-out/"
    }
}

def create_output(result):
    "create output structure for single run"

    cm_count_to_crop_to_vals = defaultdict(lambda: defaultdict(dict))
    if len(result.get("data", [])) > 0 and len(result["data"][0].get("results", [])) > 0:

        for data in result.get("data", []):
            results = data.get("results", [])
            oids = data.get("outputIds", [])

            #skip empty results, e.g. when event condition haven't been met
            if len(results) == 0:
                continue

            assert len(oids) == len(results)
            for kkk in range(0, len(results[0])):
                vals = {}

                for iii in range(0, len(oids)):
                    oid = oids[iii]
                    val = results[iii][kkk]

                    name = oid["name"] if len(oid["displayName"]) == 0 else oid["displayName"]

                    if isinstance(val, types.ListType):
                        for val_ in val:
                            vals[name] = val_
                    else:
                        vals[name] = val

                if "CM-count" not in vals or "Crop" not in vals:
                    print "Missing CM-count or Crop in result section. Skipping results section."
                    continue

                cm_count_to_crop_to_vals[vals["CM-count"]][vals["Crop"]].update(vals)

    return cm_count_to_crop_to_vals

def create_template_grid(path_to_file, n_rows, n_cols):
    "0=no data, 1=data"

    with open(path_to_file) as file_:
        for header in range(0, 6):
            file_.next()

        out = np.full((n_rows, n_cols), 0, dtype=np.int8)

        row = 0
        for line in file_:
            col = 0
            for val in line.split(" "):
                out[row, col] = 0 if int(val) == -9999 else 1
                col += 1
            row += 1

        return out


HEADER = """ncols         1928
nrows         2544
xllcorner     -9345.000000
yllcorner     8000665.000000
cellsize      900
NODATA_value  -9999
"""

def write_row_to_grids(row_col_data, row, insert_nodata_rows_count, template_grid, rotation, period):
    "write grids row by row"

    row_template = template_grid[row]
    rows, cols = template_grid.shape

    make_dict_dict_nparr = lambda: defaultdict(lambda: defaultdict(lambda: np.full((cols,), -9999, dtype=np.float)))

    output_grids = {
        "sowing": {"data" : make_dict_dict_nparr(), "cast-to": "int", "digits": 0},
        "harvest": {"data" : make_dict_dict_nparr(), "cast-to": "int", "digits": 0},
        #"Year": {"data" : make_dict_dict_nparr(), "cast-to": "int", "digits": 0},
        "s-year": {"data" : make_dict_dict_nparr(), "cast-to": "int", "digits": 0},
        "h-year": {"data" : make_dict_dict_nparr(), "cast-to": "int", "digits": 0},
        "Yield": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 2},
        "NDefavg": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "TraDefavg": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "anthesis": {"data" : make_dict_dict_nparr(), "cast-to": "int", "digits": 0},
        "matur": {"data" : make_dict_dict_nparr(), "cast-to": "int", "digits": 0},
        #"Nstress1": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "TraDef1": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        #"Nstress2": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "TraDef2": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        #"Nstress3": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "TraDef3": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        #"Nstress4": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "TraDef4": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        #"Nstress5": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "TraDef5": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        #"Nstress6": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "TraDef6": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "NFert": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "NLeach": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "PercolationRate": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "Nmin": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "SumNUp": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "length": {"data" : make_dict_dict_nparr(), "cast-to": "int", "digits": 0},
        "avg-precip": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 4},
        "avg-tavg": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 1},
        "avg-tmax": {"data" : make_dict_dict_nparr(), "cast-to": "float", "digits": 1},
        "Tmax>=40": {"data" : make_dict_dict_nparr(), "cast-to": "int", "digits": 0},
    }

    # skip this part if we write just a nodata line
    if row in row_col_data:
        for col in xrange(0, cols):
            if row_template[col] == 1:
                if col in row_col_data[row]:
                    for cm_count, crop_to_data in row_col_data[row][col].iteritems():
                        for crop, data in crop_to_data.iteritems():
                            for key, val in output_grids.iteritems():
                                val["data"][cm_count][crop][col] = data.get(key, -9999)

    for key, y2c2d_ in output_grids.iteritems():
        
        key = key.replace(">=", "gt")

        y2c2d = y2c2d_["data"]
        cast_to = y2c2d_["cast-to"]
        digits = y2c2d_["digits"]
        if cast_to == "int":
            mold = lambda x: str(int(x))
        else:
            mold = lambda x: str(round(x, digits))

        for cm_count, c2d in y2c2d.iteritems():

            for crop, row_arr in c2d.iteritems():
            
                crop = crop.replace("/", "").replace(" ", "")
                path_to_file = PATHS[USER]["LOCAL_PATH_TO_OUTPUT_DIR"] + period + "/" + crop + "_in_" + rotation + "_" + key + "_" + str(cm_count) + ".asc"

                if not os.path.isfile(path_to_file):
                    with open(path_to_file, "w") as _:
                        _.write(HEADER)

                with open(path_to_file, "a") as _:

                    if insert_nodata_rows_count > 0:
                        for i in xrange(0, insert_nodata_rows_count):
                            rowstr = " ".join(map(lambda x: "-9999", row_template))
                            _.write(rowstr +  "\n")

                    rowstr = " ".join(map(lambda x: "-9999" if int(x) == -9999 else mold(x), row_arr))
                    _.write(rowstr +  "\n")
    
    if row in row_col_data:
        del row_col_data[row]


def main():
    "collect data from workers"

    config = {
        "port": "7777",
        "start-row": "0",
        "server": "cluster1"
    }
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            k,v = arg.split("=")
            if k in config:
                config[k] = v 

    local_run = False
    write_normal_output_files = True
    if write_normal_output_files:
        write_out_for_BYM = True #change if needed
    
    i = 0
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    if local_run:
        socket.connect("tcp://localhost:" + config["port"])
    else:
        socket.connect("tcp://" + config["server"] + ":" + config["port"])    
    socket.RCVTIMEO = 10000
    leave = False
    
    n_rows = 2544
    n_cols = 1928

    if not write_normal_output_files:  
        print("loading template for output...")
        template_grid = create_template_grid(PATHS[USER]["LOCAL_PATH_TO_ARCHIV"] + "Soil/Carbiocial_Soil_Raster_final.asc", n_rows, n_cols)
        datacells_per_row = np.sum(template_grid, axis=1) #.tolist()
        print("load complete")

        period_to_rotation_to_data = defaultdict(lambda: defaultdict(lambda: {
            "row-col-data": defaultdict(dict),
            "datacell-count": datacells_per_row.copy(), 
            "insert-nodata-rows-count": 0,
            "next-row": int(config["start-row"])
        }))

        debug_file = open("debug.out", "w")

    while not leave:
        try:
            result = socket.recv_json(encoding="latin-1")
        except:
            #print "no activity on socket for ", (socket.RCVTIMEO / 1000.0), "s, trying to write final data"
            #for period, rtd in period_to_rotation_to_data.iteritems():
            #    print "period:", period
            #    for rotation, data in rtd.iteritems():
            #        print "rotation:", rotation
            #        while data["next-row"] in data["row-col-data"]:# and data["datacell-count"][data["next-row"]] == 0:
            #            print "row:", data["next-row"]
            #            write_row_to_grids(data["row-col-data"], data["next-row"], data["insert-nodata-rows-count"], template_grid, rotation, period)
            #            data["insert-nodata-rows-count"] = 0 # should have written the nodata rows for this period and 
            #            data["next-row"] += 1 # move to next row (to be written)
            continue

        if result["type"] == "finish":
            print "received finish message"
            leave = True

        elif not write_normal_output_files:
            custom_id = result["customId"]
            ci_parts = custom_id.split("|")
            period = ci_parts[0]
            row = int(ci_parts[1])
            col = int(ci_parts[2])
            rotation = ci_parts[3]

            data = period_to_rotation_to_data[period][rotation]
            debug_msg = "received work result " + str(i) + " customId: " + result.get("customId", "") \
            + " next row: " + str(data["next-row"]) + " cols@row to go: " + str(data["datacell-count"][row]) + "@" + str(row) #\
            #+ " rows unwritten: " + str(data["row-col-data"].keys()) 
            print debug_msg
            debug_file.write(debug_msg + "\n")

            data["row-col-data"][row][col] = create_output(result)
            data["datacell-count"][row] -= 1

            while (data["next-row"] < n_rows and datacells_per_row[data["next-row"]] == 0) \
            or (data["next-row"] in data["row-col-data"] and data["datacell-count"][data["next-row"]] == 0):
                # if rows have been initially completely nodata, remember to write these rows before the next row with some data
                if datacells_per_row[data["next-row"]] == 0:
                    data["insert-nodata-rows-count"] += 1
                else:
                    write_row_to_grids(data["row-col-data"], data["next-row"], data["insert-nodata-rows-count"], template_grid, rotation, period)
                    debug_msg = "wrote " + rotation + " row: "  + str(data["next-row"]) + " next-row: " + str(data["next-row"]+1) + " rows unwritten: " + str(data["row-col-data"].keys())
                    print debug_msg
                    debug_file.write(debug_msg + "\n")
                    data["insert-nodata-rows-count"] = 0 # should have written the nodata rows for this period and 
                
                data["next-row"] += 1 # move to next row (to be written)

            i = i + 1
        
        elif write_normal_output_files:
            print "received work result ", i, " customId: ", result.get("customId", "")

            custom_id = result["customId"]
            ci_parts = custom_id.split("|")
            period = ci_parts[0]
            row = int(ci_parts[1])
            col = int(ci_parts[2])
            rotation = ci_parts[3]
            file_name = str(row) + "_" + str(col) + "_" + rotation + "_" + period
            

            #with open("out/out-" + str(i) + ".csv", 'wb') as _:
            with open("out/" + period + "/" + file_name + ".csv", 'wb') as _:
                writer = csv.writer(_, delimiter=",")

                sowing_dates = defaultdict(list) #for BYM
                harvest_dates = defaultdict(list) #for BYM

                for data_ in result.get("data", []):
                    results = data_.get("results", [])
                    orig_spec = data_.get("origSpec", "")
                    output_ids = data_.get("outputIds", [])

                    if not write_out_for_BYM:
                        if len(results) > 0:
                            writer.writerow([orig_spec.replace("\"", "")])
                            for row in monica_io.write_output_header_rows(output_ids,
                                                                        include_header_row=True,
                                                                        include_units_row=True,
                                                                        include_time_agg=False):
                                writer.writerow(row)

                            for row in monica_io.write_output(output_ids, results):
                                writer.writerow(row)

                        writer.writerow([])
                    
                    elif write_out_for_BYM:                        
                        calc_avg_dates = True
                        glob_rad = defaultdict(lambda: defaultdict(list)) #crop, day, list of values in the period
                        LAI = defaultdict(lambda: defaultdict(list))
                        days_after_sowing = defaultdict()
                        days_after_sowing_LAI = defaultdict()

                        for row in monica_io.write_output(output_ids, results):
                            if orig_spec == unicode('"crop"'):
                                #convert sowing and harvest to dates: fixed year to allow avg calc
                                unique_s_year = 2017
                                unique_h_year = unique_s_year + (row[2] - row[1])
                                s_date = date(unique_s_year, 1, 1) + timedelta(days=row[4]-1)
                                h_date = date(unique_h_year, 1, 1) + timedelta(days=row[5]-1)

                                sowing_dates[row[3]].append(s_date)
                                harvest_dates[row[3]].append(h_date)
                            
                            if orig_spec == unicode('"daily"'):
                                while calc_avg_dates:
                                    #find average sowing and harvest date for each crop
                                    s_h_dates = defaultdict(lambda: defaultdict())
                                    for cp in sowing_dates.keys():
                                        s_h_dates[cp]["sowing"] = (np.array(sowing_dates[cp], dtype='datetime64[s]')
                                                .view('i8').mean()
                                                .astype('datetime64[s]')
                                                .astype(datetime))
                                        s_h_dates[cp]["harvest"] = (np.array(harvest_dates[cp], dtype='datetime64[s]')
                                                .view('i8').mean()
                                                .astype('datetime64[s]')
                                                .astype(datetime))
                                    
                                    calc_avg_dates = False
                                
                                #store global radiation from avg sowing to avg harvest
                                today = row[0].split("-")
                                current_date = date(int(today[0]), int(today[1]), int(today[2]))
                                for cp in s_h_dates.keys():
                                    add_year = s_h_dates[cp]["harvest"].year - s_h_dates[cp]["sowing"].year #identify whether avg harvest is the next year
                                    if (current_date >= date(current_date.year, s_h_dates[cp]["sowing"].month, s_h_dates[cp]["sowing"].day)
                                    and current_date <= date(current_date.year + add_year, s_h_dates[cp]["harvest"].month, s_h_dates[cp]["harvest"].day)):
                                        #we're between sowing and harvest
                                        if current_date == date(current_date.year, s_h_dates[cp]["sowing"].month, s_h_dates[cp]["sowing"].day):
                                            days_after_sowing[cp] = 0 # it's sowing date -> restore the counter
                                        glob_rad[cp][days_after_sowing[cp]].append(row[3])
                                        days_after_sowing[cp] += 1
                                
                                #store LAI from sowing to harvest (specific for each year)
                                for cp in s_h_dates.keys():
                                    if row[1] == unicode(''):
                                        days_after_sowing_LAI[cp] = 0
                                    if row[1] == cp:
                                        days_after_sowing_LAI[cp] += 1
                                        LAI[cp][days_after_sowing_LAI[cp]].append(row[2])
                                                        

                #write output
                header = ["crop", "das", "Globrad", "LAI"]
                writer.writerow(header)
                for cp in s_h_dates.keys():
                    for das in glob_rad[cp].keys():
                        avg_rad = np.array(glob_rad[cp][das]).mean()
                        avg_LAI = np.array(LAI[cp][das]).mean()
                        writer.writerow([cp, das, avg_rad, avg_LAI])

            i = i + 1

    debug_file.close()

main()


