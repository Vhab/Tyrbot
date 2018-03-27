from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.commands.param_types import Const, Any, Options


@instance()
class ConfigController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.access_manager = registry.get_instance("access_manager")
        self.command_manager = registry.get_instance("command_manager")
        self.event_manager = registry.get_instance("event_manager")

    def start(self):
        pass

    @command(command="config", params=[], access_level="superadmin", description="Shows configuration options for the bot")
    def config_list_cmd(self, channel, sender, reply, args):
        sql = """SELECT
                module,
                SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) count_enabled,
                SUM(CASE WHEN enabled = 0 THEN 1 ELSE 0 END) count_disabled
            FROM
                (SELECT module, enabled FROM command_config
                UNION
                SELECT module, enabled FROM event_config
                UNION
                SELECT module, 2 FROM setting) t
            GROUP BY
                module
            ORDER BY
                module ASC"""

        data = self.db.query(sql)
        count = len(data)
        blob = ""
        current_group = ""
        for row in data:
            parts = row.module.split(".")
            group = parts[0]
            module = parts[1]
            if group != current_group:
                current_group = group
                blob += "\n<header2>" + current_group + "<end>\n"

            blob += self.text.make_chatcmd(module, "/tell <myname> config mod " + row.module) + " "
            if row.count_enabled > 0 and row.count_disabled > 0:
                blob += "<yellow>Partial<end>"
            elif row.count_disabled == 0:
                blob += "<green>Enabled<end>"
            else:
                blob += "<red>Disabled<end>"
            blob += "\n"

        reply(ChatBlob("Config (%d)" % count, blob))

    @command(command="config", params=[Const("mod"), Any("module_name")], access_level="superadmin",
             description="Shows configuration options for a specific module")
    def config_module_list_cmd(self, channel, sender, reply, args):
        module = args[1].lower()

        blob = ""

        data = self.db.query("SELECT name, description, value FROM setting WHERE module = ? ORDER BY name ASC", [module])
        if data:
            blob += "<header2>Settings<end>\n"
            for row in data:
                blob += row.description + ": "
                blob += self.text.make_chatcmd(row.value, "/tell <myname> config setting " + row.value) + "\n"

        data = self.db.query("SELECT DISTINCT command, sub_command FROM command_config WHERE module = ? ORDER BY command ASC",
                             [module])
        if data:
            blob += "\n<header2>Commands<end>\n"
            for row in data:
                command_key = self.command_manager.get_command_key(row.command, row.sub_command)
                blob += self.text.make_chatcmd(command_key, "/tell <myname> config cmd " + command_key) + "\n"

        data = self.db.query("SELECT event_type, handler, description FROM event_config WHERE module = ? "
                             "ORDER BY event_type, handler ASC",
                             [module])
        if data:
            blob += "\n<header2>Events<end>\n"
            for row in data:
                blob += row.event_type + " "
                blob += self.text.make_chatcmd(row.description, "/tell <myname> config event " + row.handler) + "\n"

        reply(ChatBlob(module + " Module Config", blob))

    @command(command="config", params=[Const("cmd"), Any("cmd_name"), Options(["enable", "disable"]), Any("channel")], access_level="superadmin",
             description="Enable or disable a command")
    def config_cmd_status_cmd(self, channel, sender, reply, args):
        cmd_name = args[1].lower()
        action = args[2].lower()
        cmd_channel = args[3].lower()
        command_str, sub_command_str = self.command_manager.get_command_key_parts(cmd_name)
        enabled = 1 if action == "enable" else 0

        if cmd_channel != "all" and not self.command_manager.is_command_channel(cmd_channel):
            reply("Unknown command channel '%s'." % cmd_channel)
            return

        sql = "UPDATE command_config SET enabled = ? WHERE command = ? AND sub_command = ?"
        params = [enabled, command_str, sub_command_str]
        if cmd_channel != "all":
            sql += " AND channel = ?"
            params.append(cmd_channel)

        count = self.db.exec(sql, params)
        if count == 0:
            reply("Could not find command '%s' for channel '%s'." % (cmd_name, cmd_channel))
        else:
            if cmd_channel == "all":
                reply("Command '%s' has been %sd successfully." % (cmd_name, action))
            else:
                reply("Command '%s' for channel '%s' has been %sd successfully." % (cmd_name, channel, action))

    @command(command="config", params=[Const("cmd"), Any("cmd_name"), Const("access_level"), Any("channel"), Any("access_level")], access_level="superadmin",
             description="Change access_level for a command")
    def config_cmd_access_level_cmd(self, channel, sender, reply, args):
        cmd_name = args[1].lower()
        cmd_channel = args[2].lower()
        access_level = args[3].lower()
        command_str, sub_command_str = self.command_manager.get_command_key_parts(cmd_name)

        if cmd_channel != "all" and not self.command_manager.is_command_channel(cmd_channel):
            reply("Unknown command channel '%s'." % cmd_channel)
            return

        if not self.access_manager.get_access_level_by_label(access_level):
            reply("Unknown access level '%s'." % access_level)
            return

        sql = "UPDATE command_config SET access_level = ? WHERE command = ? AND sub_command = ?"
        params = [access_level, command_str, sub_command_str]
        if cmd_channel != "all":
            sql += " AND channel = ?"
            params.append(cmd_channel)

        count = self.db.exec(sql, params)
        if count == 0:
            reply("Could not find command '%s' for channel '%s'." % (cmd_name, cmd_channel))
        else:
            if cmd_channel == "all":
                reply("Access level '%s' for command '%s' has been set successfully." % (access_level, cmd_name))
            else:
                reply("Access level '%s' for command '%s' on channel '%s' has been set successfully." % (access_level, cmd_name, channel))

    @command(command="config", params=[Const("event"), Any("event_type"), Any("event_handler"), Options(["enable", "disable"])],
             access_level="superadmin",
             description="Enable or disable an event")
    def config_event_status_cmd(self, channel, sender, reply, args):
        event_type = args[1].lower()
        event_handler = args[2].lower()
        action = args[3].lower()
        event_base_type, event_sub_type = self.event_manager.get_event_type_parts(event_type)
        enabled = 1 if action == "enable" else 0

        if not self.event_manager.is_event_type(event_base_type):
            reply("Unknown event type '%s'." % event_type)
            return

        count = self.db.exec("UPDATE event_config SET enabled = ? "
                             "WHERE event_type = ? AND event_sub_type = ? AND handler LIKE ?",
                             [enabled, event_base_type, event_sub_type, event_handler])

        if count == 0:
            reply("Could not find event for type '%s' and handler '%s'." % (event_type, event_handler))
        else:
            reply("Event type '%s' for handler '%s' has been %sd successfully." % (event_type, event_handler, action))