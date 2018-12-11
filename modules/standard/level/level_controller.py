from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.db import DB
from core.command_param_types import Int


@instance()
class LevelController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("lvl", "level")
        self.command_alias_service.add_alias("pvp", "level")
        self.command_alias_service.add_alias("missions", "mission")

    @command(command="level", params=[Int("level")], access_level="all",
             description="Show information about a character level")
    def level_cmd(self, request, level):
        row = self.get_level_info(level)

        if row:
            msg = "<white>L %d: Team %d-%d<end><highlight> | <end><cyan>PvP %d-%d<end><highlight> | <end><orange>Missions %s<end><highlight> | <end><blue>%d token(s)<end>" %\
                  (row.level, row.team_min, row.team_max, row.pvp_min, row.pvp_max, row.missions, row.tokens)
            return msg
        else:
            return "Level must be between <highlight>1<end> and <highlight>220<end>."

    @command(command="mission", params=[Int("mission_level")], access_level="all",
             description="Show what character levels can roll a specified mission level")
    def mission_cmd(self, request, level):
        if 1 <= level <= 250:
            levels = []
            data = self.db.query("SELECT * FROM level")
            str_level = str(level)
            for row in data:
                if str_level in row.missions.split(","):
                    levels.append(str(row.level))

            return "QL%d missions can be rolled from these levels: %s" % (level, " ".join(levels))
        else:
            return "Mission level must be between <highlight>1<end> and <highlight>250<end>."

    @command(command="xp", params=[Int("start_level"), Int("end_level", is_optional=True)], access_level="all",
             description="Show the amount of XP needed to reach a certain level")
    def xp_range_cmd(self, request, start_level, end_level):
        end_level = end_level or start_level + 1

        if start_level == end_level:
            return "Start level must be different than end level."

        if start_level > end_level:
            start_level, end_level = end_level, start_level

        if 1 <= start_level <= 220 and 1 <= end_level <= 220:
            if end_level <= 200:
                xp = self.db.query_single("SELECT SUM(xpsk) AS total_xp FROM level WHERE level >= ? AND level < ?", [start_level, end_level])
                needed = "<highlight>%s<end> XP" % self.util.format_number(xp.total_xp)
            elif start_level >= 200:
                sk = self.db.query_single("SELECT SUM(xpsk) AS total_sk FROM level WHERE level >= ? AND level < ?", [start_level, end_level])
                needed = "<highlight>%s<end> SK" % self.util.format_number(sk.total_sk)
            else:
                xp = self.db.query_single("SELECT SUM(xpsk) AS total_xp FROM level WHERE level >= ? AND level < 200", [start_level])
                sk = self.db.query_single("SELECT SUM(xpsk) AS total_sk FROM level WHERE level >= 200 AND level < ?", [end_level])
                needed = "<highlight>%s<end> XP and <highlight>%s<end> SK" % (self.util.format_number(xp.total_xp), self.util.format_number(sk.total_sk))

            return "From the beginning of level <highlight>%d<end> you need %s to reach level <highlight>%d<end>" % (start_level, needed, end_level)
        else:
            return "Level must be between <highlight>1<end> and <highlight>219<end>."

    @command(command="axp", params=[], access_level="all",
             description="Show information about alien levels")
    def axp_single_cmd(self, request):
        data = self.db.query("SELECT * FROM alien_level ORDER BY alien_level ASC")

        blob = ""
        for row in data:
            blob += "AI Level <green>%d<end> - %s - <highlight>%s<end> - Min Level: %d\n" % (row.alien_level, self.util.format_number(row.axp), row.defender_rank, row.min_level)

        return ChatBlob("Alien Levels", blob)

    def get_level_info(self, level):
        return self.db.query_single("SELECT * FROM level WHERE level = ?", [level])
