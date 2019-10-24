import json
import time
from datetime import datetime, timedelta
import os
import urllib.request as request
import xlsxwriter
from appJar import gui

CONFIG_PATH = "./osuconfig.json"


def get_user_recent(api_key, user_id):
    contents = request.urlopen(f"https://osu.ppy.sh/api/get_user_recent?k={api_key}&u={user_id}").read()
    api_data = json.loads(contents)

    for i, play in enumerate(api_data):
        count0 = int(play["countmiss"])
        count50 = int(play["count50"])
        count100 = int(play["count100"])
        count300 = int(play["count300"])
        
        acc = (50 * count50 + 100 * count100 + 300 * count300) / (300 * (count0 + count50 + count100 + count300))
       
        api_data[i]["acc"] = str(round(acc, 4))

    return api_data


def get_user(api_key, user_id):
    contents = request.urlopen(f"https://osu.ppy.sh/api/get_user?k={api_key}&u={user_id}").read()
    api_data = json.loads(contents)
    
    return api_data[0]


def get_beatmap(api_key, bm_id):
    contents = request.urlopen(f"https://osu.ppy.sh/api/get_beatmaps?k={api_key}&b={bm_id}").read()
    api_data = json.loads(contents)
    
    return api_data[0]


def load_json(path):
    if os.path.isfile(path): 
        f = open(path, "r")
        json_data = json.load(f)
        f.close()
    else:
        json_data = []

    return json_data


def save_json(path, json_data):
    f = open(path, "w")
    json.dump(json_data, f)
    f.close()


def create_config(database_path="", excel_path="", api_key="", user_id="", start_date="", start_playcount="", rate="", last_userids="", last_bmids=""):
    config = {
        "database_path": database_path,
        "excel_path": excel_path,
        "api_key": api_key,
        "user_id": user_id,
        "start_date": start_date,
        "start_playcount": start_playcount,
        "rate": rate,
        "last_userids": last_userids,
        "last_bmids": last_bmids
    }

    return config


def add_new(recent_data, database):
    last_ten = database[-30:]

    for play in recent_data:
        if not play in last_ten:
            if play["rank"] != "F":
                database.append(play)
    
    return database


def update_beatmap_info(api_key, bm_info, recent_data): #does nothing
    for play in recent_data:
        bm_id = play["beatmap_id"]

        if not bm_id in bm_info:
            bm_info[bm_id] = get_beatmap(api_key, bm_id)
    return bm_info


def missing_plays(user_data, rate, start_date="", start_playcount=""):
    start_date = datetime.now() if start_date == "" else datetime.fromisoformat(start_date) # = value_when_true if condition else value_when_false
    start_playcount = int(user_data["playcount"]) if start_playcount == "" else int(start_playcount)
    
    delta = datetime.now() - start_date
    days = delta.days + 1

    target = start_playcount + days * rate
    missing = target - int(user_data["playcount"])

    return missing, str(start_date), str(start_playcount)


def database_to_excel(database, path, user_ids=[], bm_ids=[]):
    workbook = xlsxwriter.Workbook(path)
    worksheet = workbook.add_worksheet()

    row = 1
    for c in database:
        if not c["user_id"] in user_ids and len(user_ids) != 0:
            continue

        if not c["beatmap_id"] in bm_ids and len(bm_ids) != 0:
            continue

        for col, key in enumerate(c):
            if row - 1 == 0:
                worksheet.write(row - 1, col, key)

            item = c[key]
            
            worksheet.write(row, col, item)

        row = row + 1
    
    workbook.close()


def create_gui(data):
    app = gui("OsuSchtats", "400x400")

    def excel_click(btn):
        usrids = data.config["last_userids"]
        bmids = data.config["last_bmids"]

        app.setEntry("User-Id", usrids)
        app.setEntry("BM-Id", bmids)

        app.showSubWindow("excel_window")

    def config_click(btn):
        app.setEntry("Database Path", data.config["database_path"])
        app.setEntry("Excel Path", data.config["excel_path"])
        app.setEntry("API Key", data.config["api_key"])
        app.setEntry("User ID", data.config["user_id"])
        app.setEntry("Daily Rate", data.config["rate"])
        app.setEntry("Start Date", data.config["start_date"])
        app.setEntry("Start Playcont", data.config["start_playcount"])

        app.showSubWindow("config_window")
        app.config_window_shown = True
        
    def config_save_click(btn):
        data.config["database_path"] = app.getEntry("Database Path")
        data.config["excel_path"] = app.getEntry("Excel Path")
        data.config["api_key"] = app.getEntry("API Key")
        data.config["user_id"] = app.getEntry("User ID")
        data.config["rate"] = app.getEntry("Daily Rate")
        data.config["start_date"] = app.getEntry("Start Date")
        data.config["start_playcount"] = app.getEntry("Start Playcont")

        data.config_exists = True

    def on_config_window_close():
        app.config_window_shown = False
        return True

    def on_form_create():
        app.thread(loop, app, data)


    def on_from_close():
        save_json(CONFIG_PATH, data.config)
        save_json(data.config["database_path"], data.database)
        return True


    def create_click(button):
        usrids = app.getEntry("User-Id")
        bmids = app.getEntry("BM-Id")

        list_uids = usrids.replace(" ", "")
        list_uids = list_uids.split(",")
        list_uids = list_uids if list_uids[0] != "" else []

        list_bmids = bmids.replace(" ", "")
        list_bmids = list_bmids.split(",")
        list_bmids = list_bmids if list_bmids[0] != "" else []

        data.config["last_userids"] = usrids
        data.config["last_bmids"] = bmids

        database_to_excel(data.database, data.config["excel_path"], user_ids= list_uids, bm_ids= list_bmids)
        

    app.addLabel("playcount_label", "Missing: 0")
    app.addLabel("missing_label", "Missing: 0")
    app.setOnTop(stay=True)
    app.addButton("Excel Settings", excel_click)
    app.addButton("User Settings", config_click)

    #subwindow excel
    app.startSubWindow("excel_window", title="Excel Window")
    app.addLabelEntry("User-Id",)
    app.addLabelEntry("BM-Id",)
    app.addButton("Export Excel", create_click)
    app.setOnTop(stay=True)
    app.stopSubWindow()

    #subwindow config
    app.startSubWindow("config_window", title="Config Window")
    app.addLabelEntry("Database Path")
    app.addLabelEntry("Excel Path")
    app.addLabelEntry("API Key")
    app.addLabelEntry("User ID")
    app.addLabelEntry("Daily Rate")
    app.addLabelEntry("Start Date")
    app.addLabelEntry("Start Playcont")
    app.addButton("Save", config_save_click)
    app.config_window_shown = False
    app.setOnTop(stay=True)
    app.setStopFunction(on_config_window_close)
    app.stopSubWindow()

    app.setStartFunction(on_form_create)
    app.setStopFunction(on_from_close)

    return app


def loop(app, data):
    while True:
        if not data.config_exists:
            if not app.config_window_shown:
                app.queueFunction(app.showSubWindow, "config_window")
                app.config_window_shown = True
            time.sleep(1)
            continue

        try:
            recent_data = get_user_recent(data.config["api_key"], data.config["user_id"])
            user_data = get_user(data.config["api_key"], data.config["user_id"])
            
            data.database = add_new(recent_data, data.database)

            missing, start_date, start_playcount = missing_plays(user_data, int(data.config["rate"]), start_date=data.config["start_date"], start_playcount=data.config["start_playcount"])
            data.config["start_date"] = start_date
            data.config["start_playcount"] = start_playcount

            app.queueFunction(app.setLabel, "playcount_label", f"Playcount: {user_data['playcount']}")
            app.queueFunction(app.setLabel, "missing_label", f"Missing: {missing}")

            time.sleep(10)
        except Exception as e:
            app.queueFunction(app.soundError)
            data.config_exists = False
            print(e)


def main():
    config = load_json(CONFIG_PATH)
    database = load_json(config["database_path"] if len(config) != 0 else "")
    data = Data(config, database)

    app = create_gui(data)
    app.go()


class Data:
    def __init__(self, config, database):
        self.config_exists = len(config) != 0
        self.config = config if self.config_exists else create_config()
        self.database = database


if __name__ == "__main__":
    main()