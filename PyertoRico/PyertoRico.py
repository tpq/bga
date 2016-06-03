#!/usr/bin/env python

# Import dependencies
import pandas as pd
import webbrowser
import requests
import re

class GameSeries:
    
    def __init__(self, tableIDs):
        games = []
        for tableID in tableIDs:
            games.append(Game(tableID))
        self.games = games
        
class PuertoRicoSeries(GameSeries):
    
    def __init__(self, tableIDs):
        games = []
        for tableID in tableIDs:
            games.append(PuertoRico(tableID))
        self.games = games
        
class Game:
    
    # Initialize a Game object from the html "logs" of a BGA game
    def __init__(self, tableID):
        self.tableID = tableID
        self.roles = Game.get(tableID)
        self.turnorder = [role.player_name for role in self.roles]
        self.roleorder = [role.rol_type for role in self.roles]
        
    # Parse the game into a list of "role blocks"
    def get(tableID):
        
        # Open webpage with browser to instance a game "log"
        # User must log into Board Game Arena on browser
        html = "http://en.boardgamearena.com/gamereview" + "?table=" + tableID
        webbrowser.open(html, autoraise = False)
        
        # Get the html "log" for a single game
        target_url = "http://en.boardgamearena.com/archive/archive/logs.html"
        params = {"table": str(tableID), "translated": "true"}
        req = requests.get(target_url, params = params)
        log = req.text
        
        # Index all role changes
        index_role = []
        loc = 0
        while loc > -1:
            index_role.append(loc)
            loc = log.find("[\"rol_type_tr\"],\"player_name\"", loc + 1)
        
        # Ignore the first "role block" as a superfluous header
        # Organize remaining data into list of Role objects
        roles = []
        for i in range(1, len(index_role)):
            start = index_role[i]
            if(i == len(index_role) - 1):
                end = len(log) - 1     
            else:
                end = index_role[i + 1] - 1
            role_new = Role(log[start:end])
            roles.append(role_new)
        
        # Return a list of Role objects
        return(roles)
        
# Define PuertoRico as a sub-class of Game
# While the Game object includes methods general to (all of?) BGA,
#  this object includes methods specific to Puerto Rico.
class PuertoRico(Game):
    
    def __init__(self, tableID):
        Game.__init__(self, tableID)
        
    def tabulate(self):
    
        blds = pd.Series(
        [int(i) for i in "1" * 6] +
        [int(i) for i in "2" * 6] +
        [int(i) for i in "3" * 6] +
        [int(i) for i in "4" * 5],
        index =
        ["small indigo plant", "small sugar mill",
         "small market", "hacienda", "construction hut",
         "small warehouse"] +
        ["indigo plant", "sugar mill", "hospice", "office",
         "large market", "large warehouse"] +
        ["tobacco storage", "coffee roaster", "factory",
         "university", "harbor", "wharf"] +
        ["guild hall", "customs house", "residence",
         "city hall", "fortress"]
         )
        
        # Build a template that tabulates the game progress for each player
        plants_template = pd.DataFrame({
        "vp_ship": 0, "vp_bld": 0, "vp_bonus": 0, "vp_harbor": 0,
        "colonists": 0, "dblns": 0, "plant_quarry": 0, "plant_corn": 0,
        "plant_indigo": 0, "plant_sugar": 0, "plant_tobacco": 0,
        "plant_coffee": 0, "plant_rand": 0
        },
        index = [i for i in range(0, len(self.roles))]
        )
        
        # Build a template that tabulates buildings acquired
        blds_template = pd.DataFrame(blds).copy().T
        for i in range(0, len(self.roles)):
            blds_template.loc[i] = 0
        
        # Merge plants_template with blds_template
        game_template = pd.concat([plants_template, blds_template], axis = 1)
        
        # Give each player a game_template
        overview = {plyr: game_template.copy() for plyr in set(self.turnorder)}
    
        for i, role in enumerate(self.roles):
            
            # Find how a player benefited from each event in the role
            for event in role.role:
                
                if any([(name in event) for name in set(self.turnorder)]):
                    doer = [name for name in set(self.turnorder)
                            if ("$"+name in event)][0]
                else:
                    continue 
                
                if "doubloon from the role card" in event:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer]["dblns"][i] += dblns
                
                # settler phase
                if "got a new plantation" in event:
                    if "got a new plantation from the deck" in event:
                        overview[doer]["plant_rand"][i] += 1
                    else:
                        plants = ["corn", "indigo", "sugar",
                                  "tobacco", "coffee"]
                        new = [plt for plt in plants if ("$"+plt) in event][0]
                        overview[doer]["plant_"+new][i] += 1
                
                if "got a new quarry" in event:
                    overview[doer]["plant_quarry"][i] += 1
                
                # builder phase
                if "bought a new building for" in event:
                    new = [bld for bld in blds.index if ("$"+bld in event)][0]
                    cost = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer][new][i] += 1
                    overview[doer]["vp_bld"][i] += blds[new]
                    overview[doer]["dblns"][i] -= cost
                
                # captain phase
                if "victory point for shipping" in event:
                    if "for shipping during the game" not in event:
                        total = int(re.findall("\$[0-9]+\s", event)[0][1:])
                        overview[doer]["vp_ship"][i] += total
                
                if "victory points for shipping" in event:
                    if "for shipping during the game" not in event:
                        total = int(re.findall("\$[0-9]+\s", event)[0][1:])
                        overview[doer]["vp_ship"][i] += total
                
                if "victory point from his harbor" in event:
                    total = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer]["vp_harbor"][i] += total
                
                if "victory point as his privilege" in event:
                    total = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer]["vp_ship"][i] += total
                
                # mayor phase
                if "colonist from the ship" in event:
                    total = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer]["colonists"][i] += total
                
                if "colonists from the ship" in event:
                    total = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer]["colonists"][i] += total
                
                if "colonist from the supply as his privilege" in event:
                    overview[doer]["colonists"][i] += 1
                
                # craftsman phase
                if "doubloon from his factory" in event:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer]["dblns"][i] += dblns              
                
                if "doubloons from his factory" in event:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer]["dblns"][i] += dblns    
                
                # trader phase
                if "from the sale" in event:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer]["dblns"][i] += dblns
                
                if len(re.findall("from his \w* markets?", event)) > 0:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer]["dblns"][i] += dblns
                
                if "doubloon as his privilege" in event:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer]["dblns"][i] += dblns
                
                # prospector phase
                if len(re.findall("doubloon$", event)) > 0:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer]["dblns"][i] += dblns
                
                # tally bonus points
                if "bonus points" in event:
                    vp = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    overview[doer]["vp_bonus"][i] += vp
                
        return(overview)
        
    def cumsum(self):        
        tabs = self.tabulate()
        cs = {}
        for plyr in set(self.turnorder):
            colSums = [sum(tabs[plyr][col]) for col in tabs[plyr].columns]
            cs.update({plyr: pd.Series(colSums, index = tabs[plyr].columns)})
        return(pd.DataFrame(cs))
        
    def winner(self):
        cs = self.cumsum()
        vps = ["vp_ship", "vp_bld", "vp_bonus", "vp_harbor"]
        final = {plyr: sum(cs[plyr][vps]) for plyr in set(self.turnorder)}
        best_score = max([final[plyr] for plyr in final])
        best_plyr = [plyr for plyr in final if (final[plyr] == best_score)]
        if len(best_plyr) == 1:
            return(str(best_plyr))
        else:
            return(None)
            
class Role:
    
    # Initialize a Role object by parsing a "role block"
    def __init__(self, roleblock):
      self.roleblock = roleblock
      role_summary = Role.parse(roleblock)
      self.player_name = role_summary[0]["{player_name}"]
      self.rol_type = role_summary[1]["{rol_type}"]
      self.role = role_summary[2::]
    
    # Parse each "role block" into a list of move logs
    def parse(roleblock):
        
        # Find the first 'val' that corresponds to the supplied "{key}"
        def key2val(key, rolechunk):
            key_search = "\"" + key[1:-1] + "\"" + ":"
            key_loc = rolechunk.find(key_search)
            if rolechunk[key_loc + len(key_search)] == "\"":
                start = key_loc + len(key_search) + 1
                end = rolechunk.find("\"", start)
            else:
                start = key_loc + len(key_search)
                end1 = rolechunk.find(",", start)
                end2 = rolechunk.find("}", start)
                end = min(end1, end2)
            return({key: rolechunk[start:end]})
        
        # Retrieve important role information
        keys = ("{player_name}", "{rol_type}")
        role_summary = [key2val(key, roleblock) for key in keys] 
        
        # Retrieve the role logs
        logs = []
        log_loc = 0
        while(log_loc > -1):
            
            # Locate each role log
            log_loc = roleblock.find("\"log\":", log_loc + 1)
            if log_loc == -1:
                continue
            log_val = key2val("\"log\":", roleblock[log_loc:])
            log_val = [str(val) for (i, val) in log_val.items()][0]
            if log_val == "${player_name} selected the ${rol_type_tr}":
                continue
            
            # Populate missing "${key}" details in role log
            if len(log_val) > 0:
                args = re.findall("{\w*}", log_val)
                vals = [key2val(arg, roleblock[log_loc:]) for arg in args]
                for d in vals:
                    log_val = [log_val.replace(k,v) for (k,v) in d.items()][0]
                logs.append(log_val)
        
        # Return the role summary and role logs
        return(role_summary + logs)
