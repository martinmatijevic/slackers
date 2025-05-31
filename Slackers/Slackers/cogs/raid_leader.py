import calendar
import io
from datetime import datetime

import discord
from discord.ext import commands

from utils.db_helper import add_run, add_schedule, fetch_schedule, get_run_by_date_time, remove_run, remove_schedule, schedule_exists
from utils.format_helper import format_schedule, get_username
from utils.helper import extract_mentions, get_gc_cut_obc_str, get_next_date_from_day, process_args
from utils.renaming_helper import diff_to_type_dawn, diff_to_type_obc, loot_to_type


class RaidLeader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_role("Raidleader")
    async def schedule(self, ctx):
        """Displays all scheduled runs sorted by date and time. If too long, sends as a .txt file."""

        schedule_data = fetch_schedule()
        if not schedule_data:
            await ctx.send("📭 No schedules found.")
            return

        schedule_list = await format_schedule(self.bot, ctx.guild.id, schedule_data)

        if len(schedule_list) > 2000:
            schedule_list = schedule_list.strip("```")
            file = io.StringIO(schedule_list)  # Use in-memory file
            await ctx.send(
                "📂 Schedule is too long to display, sending as a file:",
                file=discord.File(file, filename="schedule.txt"),
            )
        else:
            await ctx.send(schedule_list)

    @commands.command()
    @commands.has_role("Raidleader")
    async def addschedule(self, ctx, id: str, date: str, time: str, difficulty: str, type: str, rl_id: int, gc_id: int, community: str):
        """
        Adds a schedule to the database.

        Arguments:
            run_id : str
                Raid ID from community website.
            date : str
                Date in the format DD/MM.
            time : str
                Time in the format HH:MM.
            difficulty : str
                NM/HC/MM representing normal/heroic/mythic.
            type : str
                Saved/Unsaved/VIP.
            rl_id : str
                Discord ID of raid leader.
            gc_id : str
                Discord ID of gold collector.
            community : str
                Community - OBC/Dawn.

        Example:
            .addschedule 10923801293 14/01 16:30 HC VIP 123823668265615360 123823668265615360 Dawn
        """

        # Validate date and time
        try:
            current_year = datetime.now().year
            full_date = f"{date}/{current_year}"
            datetime.strptime(full_date, "%d/%m/%Y")  # Validate date format
            datetime.strptime(time, "%H:%M")  # Validate time format
        except ValueError:
            await ctx.send("❌ Invalid date or time format! Use `.addschedule run_id DD/MM HH:MM difficulty type rl_id gc_id community`")
            return

        # Store in the database
        add_schedule(id, full_date, time, difficulty, type, rl_id, gc_id, community)

        # Confirmation message
        await ctx.send(
            f"✅ Schedule added!\n Run ID: `{id}`\n Date: `{full_date}`\n Time: `{time}`\n Difficulty: `{difficulty}`\n Type: `{type}`\n RL: `{await get_username(self.bot, ctx.guild.id, rl_id)}`\n GC: `{await get_username(self.bot, ctx.guild.id, gc_id)}`\n Community: `{community}`"
        )

    @commands.command()
    @commands.has_role("Raidleader")
    async def removeschedule(self, ctx, id: str):
        """
        Removes a run from the schedule database.

        Arguments:
            run_id : str
                Raid ID from community website.

        Example:
            .removeschedule 10923801293
        """

        success = remove_schedule(id)

        if success:
            await ctx.send(f"✅ Schedule with Run ID `{id}` has been removed.")
        else:
            await ctx.send(f"❌ No schedule found with Run ID: `{id}`")

    @commands.command()
    @commands.has_role("Raidleader")
    async def removerun(self, ctx, id: str):
        """
        Removes a run from the database and removes balances from that run.

        Arguments:
            run_id : str
                Raid ID from community website.

        Example:
            .removerun 10923801293
        """

        success = remove_run(id, self.bot)

        if success:
            await ctx.send(f"✅ Run with ID `{id}` has been removed.")
        else:
            await ctx.send(f"❌ No run found with ID: `{id}`")

    @commands.command()
    @commands.has_role("Raidleader")
    async def dawn(self, ctx, run_id: str, pot: str, *args):
        """
        Generates the ATD for Dawn and updates balances.

        Arguments:
            run_id : str
                Raid ID from Dawn website.
            pot : str
                Pot of the run from Dawn website (you can write it as 1000k or 1000000).
            *args : Optional flags:
                -rl : No raid leader cut.
                -gc : No gold collector cut.
                -cl @booster1 @booster2 : Assigns co-leaders (20% more cut).
                -bc @booster1 number @booster2 number : Manually set boosters boss count.

        Example:
            .dawn 10923801293 2560k -rl -gc -bc @lovac 3 -cl @trix
        """

        try:
            parts = ctx.channel.name.split("-")
            day_str, time_str = parts[0], parts[1]  # Extract "fri", "1700"

            run_date = get_next_date_from_day(day_str)
            run_time = f"{time_str[:2]}:{time_str[2:]}"  # Convert "1700" -> "17:00"

            if not run_date:
                await ctx.send("❌ Invalid day format in channel name.")
                return

            run = get_run_by_date_time(run_date, run_time)

            if run:
                run_id_from_schedule, _, _, _, _, _, _, community = run
                if run_id_from_schedule != run_id:
                    await ctx.send("❌ Dumbass you are using wrong channel.")
                    return
                if community != "Dawn":
                    await ctx.send(f"❌ Dumbass you are using wrong command this is {community} run.")
                    return
            else:
                await ctx.send("❌ No schedule entry found for this run_id.")
                return

            raid_helper_id = 579155972115660803  # Raid-Helper bot's user ID

            # Fetch the schedule entry for the given run_id
            schedule_entry = schedule_exists(run_id)  # Reusing the existing method
            if not schedule_entry:
                await ctx.send("❌ No schedule entry found for this run_id.")
                return

            # Extract date, time, difficulty, and type from the schedule
            _, run_date, run_time, diff, type, rl_id, gc_id, community = schedule_entry
            difficulty = diff_to_type_dawn(diff)
            team_type = loot_to_type(type)

            # Strip the year and leading zeros from date and time
            # Date formatting (DD/MM/YYYY -> D/M)
            date_parts = run_date.split("/")
            date_str = f"{int(date_parts[0])}/{int(date_parts[1])}"

            # Time formatting (HH:MM -> H:MM)
            time_parts = run_time.split(":")
            time_str = f"{time_parts[0]}:{time_parts[1]}"

            # Parse pot (e.g., "1000k" or "1000000")
            if "k" in pot.lower():
                pot_value = int(pot.replace("k", "")) * 1000
            else:
                pot_value = int(pot)

            # Search for the latest Raid-Helper message with multiple mentions
            async for message in ctx.channel.history(limit=1000):  # Adjust limit if needed
                if message.author.id == raid_helper_id and len(message.mentions) > 1:
                    # Extract mentions
                    mentioned_ids = extract_mentions(message.content)

                    if mentioned_ids:
                        await ctx.send("<:cutswhen:1244256509546725438>")
                        mention_dict = {mention_id: 8 for mention_id in mentioned_ids}
                        co_lead_boosters, modified_cuts, no_raid_leader_cut, no_gold_collector_cut = process_args(args, ctx.author.id)
                        merged_dict = {**mention_dict, **modified_cuts}
                        # Modify mentions to handle rl_id and flags
                        formatted_mentions = []
                        for key, value in merged_dict.items():
                            if key in co_lead_boosters:
                                formatted_mentions.append(f"{key}:{value}:co-lead")
                            elif key == rl_id:
                                if no_raid_leader_cut:
                                    formatted_mentions.append(f"{key}:{value}:")
                                else:
                                    formatted_mentions.append(f"{key}:{value}:lead")
                            else:
                                formatted_mentions.append(f"{key}:{value}:")
                        mentions_str = ",".join(formatted_mentions)  # Joining all mentions with appropriate formatting

                        for key in co_lead_boosters:
                            if key in merged_dict:
                                merged_dict[key] = merged_dict[key] * 1.2

                        # Use "X" for GC if the flag is set
                        gc_str = "X" if no_gold_collector_cut else gc_id

                        # Creating the formatted message
                        formatted_message = f"```\n{date_str}\n{time_str}\n{difficulty}\n{team_type}\n{pot_value}\n{mentions_str}\n{gc_str}\n{run_id}```"
                        booster_cut = add_run(
                            self.bot,
                            run_id,
                            run_date,
                            run_time,
                            difficulty,
                            team_type,
                            pot_value,
                            rl_id,
                            gc_id,
                            merged_dict,
                            community,
                            rl_cut_shared=no_raid_leader_cut,
                            gc_cut_shared=no_gold_collector_cut,
                        )
                        if booster_cut:
                            channel_id = 1288360490543616062
                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                await channel.send(
                                    f"Cut for {date_str} {time_str} {diff} {type} in {community} was roughly {f'{booster_cut:,}'.replace(',', '.')} gold."
                                )
                            await ctx.send(f"Cut for this run was roughly {f'{booster_cut:,}'.replace(',', '.')} gold.")
                        mention_details = []
                        for mention, value in merged_dict.items():
                            user = await self.bot.fetch_user(int(mention))
                            if user:
                                mention_details.append(f"{user.id} - {user.mention} - {value}")
                            else:
                                mention_details.append(f"{mention} - (Unknown User) - {value}")

                        mention_message = "\n".join(mention_details)
                        if ctx.author.id != 123823668265615360:
                            await ctx.author.send(
                                f"**Mentioned Users:**\n{mention_message}\n**ATD for https://discord.com/channels/1129393746123964476/1231972793139331246:**\n{formatted_message}"
                            )

                        # Send DM to you (always)
                        owner = await ctx.bot.fetch_user(123823668265615360)
                        if owner:
                            await owner.send(
                                f"**Mentioned Users:**\n{mention_message}\n**Invoked by:** {ctx.author.mention}\n**ATD for https://discord.com/channels/1129393746123964476/1231972793139331246:**\n{formatted_message}"
                            )

                    else:
                        await ctx.send("❌ No valid mentions found in the message.")
                    return

            await ctx.send("❌ No recent Raid-Helper messages with multiple mentions found.")
        except Exception as e:
            print(e)

    @commands.command()
    @commands.has_role("Raidleader")
    async def obc(self, ctx, run_id: str, pot: str, *args):
        """
        Generates the ATD for OBC and updates balances.

        Arguments:
            run_id : str
                Raid ID from OBC website.
            pot : str
                Pot of the run from OBC website (you can write it as 1000k or 1000000).
            *args : Optional flags:
                -rl : No raid leader cut.
                -gc : No gold collector cut.
                -bc @booster1 number @booster2 number : Manually set boosters boss count.

        Example:
            .obc 10923801293 2560k -rl -gc -bc @lovac 3
        """

        try:

            parts = ctx.channel.name.split("-")
            day_str, time_str = parts[0], parts[1]  # Extract "fri", "1700"

            run_date = get_next_date_from_day(day_str)
            run_time = f"{time_str[:2]}:{time_str[2:]}"  # Convert "1700" -> "17:00"

            if not run_date:
                await ctx.send("❌ Invalid day format in channel name.")
                return

            run = get_run_by_date_time(run_date, run_time)

            if run:
                run_id_from_schedule, _, _, _, _, _, _, community = run
                if run_id_from_schedule != run_id:
                    await ctx.send("❌ Dumbass you are using wrong channel.")
                    return
                if community != "OBC":
                    await ctx.send(f"❌ Dumbass you are using wrong command this is {community} run.")
                    return
            else:
                await ctx.send("❌ No schedule entry found for this run_id.")
                return

            raid_helper_id = 579155972115660803  # Raid-Helper bot's user ID

            # Fetch the schedule entry for the given run_id
            schedule_entry = schedule_exists(run_id)  # Reusing the existing method
            if not schedule_entry:
                await ctx.send("❌ No schedule entry found for this run_id.")
                return

            # Extract date, time, difficulty, and type from the schedule
            _, run_date, run_time, diff, type, rl_id, gc_id, community = schedule_entry
            difficulty = diff_to_type_obc(diff)
            team_type = loot_to_type(type)

            title = f"Type of Boost: Slackers {difficulty} {team_type}"
            # Convert "DD/MM/YYYY" to "MON/DD"
            dt = datetime.strptime(run_date, "%d/%m/%Y")
            month_abbr = calendar.month_abbr[dt.month].upper()
            date_str = f"Date: {month_abbr}/{dt.day:02d}"

            # Time formatting (HH:MM -> HH:MM)
            time_parts = run_time.split(":")
            time_str = f"Time: {time_parts[0]}:{time_parts[1]}"

            # Parse pot (e.g., "1000k" or "1000000")
            pot_value = int(pot.replace("k", "")) * 1000 if "k" in pot.lower() else int(pot)
            pot_str = f"Pot: {pot_value // 1000}k" if pot_value % 1000 == 0 else str(pot_value)

            _, modified_cuts, no_raid_leader_cut, no_gold_collector_cut = process_args(args, ctx.author.id)
            leader_cut = "LeaderCut: TO_POT" if no_raid_leader_cut else "LeaderCut: TO_LEADER"
            logs = "Logs: https://www.warcraftlogs.com/"
            run_str = f"Run ID: {run_id}"

            # Search for the latest Raid-Helper message with multiple mentions
            async for message in ctx.channel.history(limit=1000):  # Adjust limit if needed
                if message.author.id == raid_helper_id and len(message.mentions) > 1:
                    # Extract mentions
                    mentioned_ids = extract_mentions(message.content)

                    if mentioned_ids:
                        await ctx.send("<:cutswhen:1244256509546725438>")
                        mention_dict = {mention_id: 8 for mention_id in mentioned_ids}
                        merged_dict = {**mention_dict, **modified_cuts}
                        # Modify mentions to handle rl_id and flags
                        formatted_mentions = []
                        for key, value in merged_dict.items():
                            if key == rl_id:
                                if no_raid_leader_cut:
                                    if value == 8:
                                        formatted_mentions.append(f"<@{key}>")
                                    else:
                                        formatted_mentions.append(f"<@{key}> {value}/8")
                                else:
                                    if value == 8:
                                        formatted_mentions.append(f"<@{key}> L")
                                    else:
                                        formatted_mentions.append(f"<@{key}> {value}/8 L")
                            else:
                                if value == 8:
                                    formatted_mentions.append(f"<@{key}>")
                                else:
                                    formatted_mentions.append(f"<@{key}> {value}/8")

                        mentions_str = "\n".join(formatted_mentions)  # Joining all mentions with appropriate formatting

                        # Use "X" for GC if the flag is set
                        gc_str = None if no_gold_collector_cut else f"<@{gc_id}> {get_gc_cut_obc_str(team_type)}"
                        if gc_str:
                            mentions_str += f"\n{gc_str}"
                        # Creating the formatted message
                        formatted_message = f"```\n{title}\n{date_str}\n{time_str}\n{pot_str}\n{leader_cut}\n{logs}\n{run_str}\n{mentions_str}```"
                        booster_cut = add_run(
                            self.bot,
                            run_id,
                            run_date,
                            run_time,
                            difficulty,
                            team_type,
                            pot_value,
                            rl_id,
                            gc_id,
                            merged_dict,
                            community,
                            rl_cut_shared=no_raid_leader_cut,
                            gc_cut_shared=no_gold_collector_cut,
                        )
                        if booster_cut:
                            channel_id = 1288360490543616062
                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                await channel.send(
                                    f"Cut for {date_str} {time_str} {diff} {type} in {community} was roughly {f'{booster_cut:,}'.replace(',', '.')} gold."
                                )
                            await ctx.send(f"Cut for this run was roughly {f'{booster_cut:,}'.replace(',', '.')} gold.")
                        mention_details = []
                        for mention, value in merged_dict.items():
                            user = await self.bot.fetch_user(int(mention))
                            if user:
                                mention_details.append(f"{user.id} - {user.mention} - {value}")
                            else:
                                mention_details.append(f"{mention} - (Unknown User) - {value}")

                        mention_message = "\n".join(mention_details)
                        if ctx.author.id != 123823668265615360:
                            await ctx.author.send(
                                f"**Mentioned Users:**\n{mention_message}\n**ATD for https://discord.com/channels/817565728965525534/1177052051939795036:**\n{formatted_message}"
                            )

                        # Send DM to you (always)
                        owner = await ctx.bot.fetch_user(123823668265615360)
                        if owner:
                            await owner.send(
                                f"**Mentioned Users:**\n{mention_message}\n**Invoked by:** {ctx.author.mention}\n**ATD for https://discord.com/channels/817565728965525534/1177052051939795036:**\n{formatted_message}"
                            )

                    else:
                        await ctx.send("❌ No valid mentions found in the message.")
                    return

            await ctx.send("❌ No recent Raid-Helper messages with multiple mentions found.")
        except Exception as e:
            print(e)


async def setup(bot):
    await bot.add_cog(RaidLeader(bot))
