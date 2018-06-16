from core.decorators import instance, command
from core.command_param_types import Any


@instance()
class SendMessageController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.character_manager = registry.get_instance("character_manager")
        self.command_manager = registry.get_instance("command_manager")

    @command(command="sendtell", params=[Any("character"), Any("message")], access_level="superadmin",
             description="Send a tell to another character from the bot")
    def sendtell_cmd(self, channel, sender, reply, args):
        char_name = args[0].capitalize()
        message = args[1]
        char_id = self.character_manager.resolve_char_to_id(char_name)
        if char_id:
            self.bot.send_private_message(char_id, message)
            reply("Your message has been sent.")
        else:
            reply("Could not find character <highlight>%s<end>." % char_name)