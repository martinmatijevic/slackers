import datetime
import json
import os
import re
import time

import discord
from bs4 import BeautifulSoup
from discord.ext import commands
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.db_helper import add_run, del_run, get_run, update_run
from utils.helper import diff_to_type, loot_to_type
from utils.python_helper import generate_2fa_code, init_selenium

load_dotenv()

# Retrieve credentials from .env
DISCORD_USERNAME = os.getenv("DISCORD_USERNAME")
DISCORD_PASSWORD = os.getenv("DISCORD_PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET")
DISCORD_ID = int(os.getenv("DISCORD_ID"))


class EditRunView(discord.ui.View):
    def __init__(self, ctx, run_id, run_data):
        super().__init__()
        self.ctx = ctx
        self.run_id = run_id
        self.user_ids = [int(user_id) for user_id in run_data["user_ids"]]
        self.run_difficulty = run_data["run_difficulty"]
        self.run_type = run_data["run_type"]
        self.run_pot = run_data["run_pot"]
        self.rl_id = run_data["rl_id"]
        self.gc_id = run_data["gc_id"]

    async def disable_all_buttons(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)

    async def interaction_check(self, interaction: discord.Interaction):
        """Ensure only the command author can interact."""
        return interaction.user == self.ctx.author

    @discord.ui.button(label="Remove User", style=discord.ButtonStyle.primary)
    async def remove_user(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Enter the user ID to remove:", ephemeral=True
        )

        def check(msg):
            return msg.author == self.ctx.author and msg.content.isdigit()

        try:
            msg = await self.ctx.bot.wait_for("message", check=check, timeout=30)
            user_to_remove = int(msg.content)

            if user_to_remove in self.user_ids:
                self.user_ids.remove(user_to_remove)
                update_run(
                    self.run_id,
                    self.user_ids,
                    self.run_difficulty,
                    self.run_type,
                    self.run_pot,
                    self.rl_id,
                    self.gc_id,
                    rl_cut_removed=False,
                    gc_cut_removed=False,
                )
                await self.ctx.send(f"✅ Removed {user_to_remove} from the run.")
            else:
                await self.ctx.send("❌ User not found in this run.")

        except TimeoutError:
            await self.ctx.send("⏳ You took too long to respond!")

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.success)
    async def add_user(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Enter the user ID to add:", ephemeral=True
        )

        def check(msg):
            return msg.author == self.ctx.author and msg.content.isdigit()

        try:
            msg = await self.ctx.bot.wait_for("message", check=check, timeout=30)
            user_to_add = int(msg.content)

            if user_to_add not in self.user_ids:
                self.user_ids.append(user_to_add)
                update_run(
                    self.run_id,
                    self.user_ids,
                    self.run_difficulty,
                    self.run_type,
                    self.run_pot,
                    self.rl_id,
                    self.gc_id,
                    rl_cut_removed=False,
                    gc_cut_removed=False,
                )
                await self.ctx.send(f"✅ Added {user_to_add} to the run.")
            else:
                await self.ctx.send("❌ This user is already in the run.")

        except TimeoutError:
            await self.ctx.send("⏳ You took too long to respond!")

    @discord.ui.button(label="Change RL", style=discord.ButtonStyle.secondary)
    async def change_rl(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Enter the new RL's user ID:", ephemeral=True
        )

        def check(msg):
            return msg.author == self.ctx.author and msg.content.isdigit()

        try:
            msg = await self.ctx.bot.wait_for("message", check=check, timeout=30)
            new_rl = int(msg.content)

            if new_rl not in self.user_ids:
                await self.ctx.send(
                    "❌ This user is not in the run and cannot be set as RL."
                )
                return

            # Swap positions in self.user_ids
            old_rl = self.rl_id
            self.rl_id = new_rl

            update_run(
                self.run_id,
                self.user_ids,
                self.run_difficulty,
                self.run_type,
                self.run_pot,
                self.rl_id,
                self.gc_id,
                rl_cut_removed=False,
                gc_cut_removed=False,
            )

            await self.ctx.send(
                f"✅ {new_rl} is now the Raid Leader, swapping places with {old_rl}."
            )

        except TimeoutError:
            await self.ctx.send("⏳ You took too long to respond!")

    @discord.ui.button(label="Change GC", style=discord.ButtonStyle.secondary)
    async def change_gc(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Enter the new GC's user ID:", ephemeral=True
        )

        def check(msg):
            return msg.author == self.ctx.author and msg.content.isdigit()

        try:
            msg = await self.ctx.bot.wait_for("message", check=check, timeout=30)
            new_gc = int(msg.content)
            self.gc_id = new_gc

            update_run(
                self.run_id,
                self.user_ids,
                self.run_difficulty,
                self.run_type,
                self.run_pot,
                self.rl_id,
                self.gc_id,
                rl_cut_removed=False,
                gc_cut_removed=False,
            )
            await self.ctx.send(f"✅ New GC is {new_gc}.")

        except TimeoutError:
            await self.ctx.send("⏳ You took too long to respond!")

    @discord.ui.button(label="Don't Include RL Cut", style=discord.ButtonStyle.danger)
    async def no_rl_cut(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.rl_id = 0
        update_run(
            self.run_id,
            self.user_ids,
            self.run_difficulty,
            self.run_type,
            self.run_pot,
            self.rl_id,
            self.gc_id,
            rl_cut_removed=True,
            gc_cut_removed=False,
        )
        await self.ctx.send("✅ Raidleader cut removed.")

    @discord.ui.button(label="Don't Include GC Cut", style=discord.ButtonStyle.danger)
    async def no_gc_cut(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.gc_id = 0
        update_run(
            self.run_id,
            self.user_ids,
            self.run_difficulty,
            self.run_type,
            self.run_pot,
            self.rl_id,
            self.gc_id,
            rl_cut_removed=False,
            gc_cut_removed=True,
        )
        await self.ctx.send("✅ Gold Collector cut removed.")

    @discord.ui.button(label="Confirm Changes", style=discord.ButtonStyle.success)
    async def confirm_changes(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.ctx.send("✅ Run updated and cuts recalculated.")
        await self.disable_all_buttons()


class RaidLeader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_role("Raidleader")
    async def edit(self, ctx, run_id: str):
        """Edit a run interactively."""
        run_data = get_run(run_id)
        if not run_data:
            await ctx.send("❌ Run not found!")
            return

        view = EditRunView(ctx, run_id, run_data)
        view.message = await ctx.send("🛠️ Select an option to edit the run:", view=view)

    @commands.command()
    @commands.has_role("Raidleader")
    async def remove(self, ctx, run_id: str):
        """Removes a run and reverses its balance changes."""
        # Check if the run exists
        run_data = get_run(run_id)
        if not run_data:
            await ctx.send("❌ Run not found!")
            return

        # Remove run from runs.db
        user_ids = run_data["user_ids"]
        run_difficulty = run_data["run_difficulty"]
        run_type = run_data["run_type"]
        run_pot = run_data["run_pot"]
        rl_id = run_data["rl_id"]
        gc_id = run_data["gc_id"]
        del_run(run_id, user_ids, run_difficulty, run_type, run_pot, rl_id, gc_id)

        await ctx.send(
            f"✅ Run `{run_id}` has been removed, and balances have been restored."
        )

    @commands.command(aliases=["attendance", "pcr"])
    @commands.has_role("Raidleader")
    async def atd(self, ctx, run_id: str):
        """Makes ATD post to be used in Dawn Mgmt discord and adds balance changes."""
        driver = init_selenium()
        driver.implicitly_wait(30)

        # Open the login page
        driver.get("https://hub.dawn-boosting.com/login")
        time.sleep(2)  # Wait for the page to load

        try:
            discord_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//button[text()="Sign in with Discord"]')
                )
            )
            discord_button.click()
            time.sleep(2)

            WebDriverWait(driver, 10).until(EC.url_contains("discord.com/login"))

            discord_username = driver.find_element(By.ID, "uid_33")
            discord_password = driver.find_element(By.ID, "uid_35")

            discord_username.send_keys(DISCORD_USERNAME)
            discord_password.send_keys(DISCORD_PASSWORD)
            discord_password.send_keys(Keys.RETURN)
            time.sleep(5)

            discord_2fa_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "inputDefault__0f084"))
            )
            two_fa_code = generate_2fa_code(TOTP_SECRET)

            discord_2fa_input.send_keys(two_fa_code)
            discord_2fa_input.send_keys(Keys.RETURN)
            time.sleep(5)

            authorize_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//button[contains(@class, "button__201d5")]/div[text()="Authorize"]',
                    )
                )
            )
            authorize_button.click()
            time.sleep(5)

            driver.get(f"https://hub.dawn-boosting.com/bookings/raids/{run_id}")
            time.sleep(5)

            page_content = driver.page_source
            soup = BeautifulSoup(page_content, "html.parser")

            actual_pot_row = soup.find("td", string="Actual Pot:").find_next("td")
            actual_pot_s = (
                actual_pot_row.text.strip()
                if actual_pot_row
                else "Actual Pot not found"
            )
            actual_pot = int(float(actual_pot_s[:-1]) * 1000)

            driver.get(f"https://hub.dawn-boosting.com/api/raids/{run_id}")
            time.sleep(5)

            json_text = driver.find_element(By.TAG_NAME, "pre").text
            data = json.loads(json_text)

            run_date_time = data.get("dateTime", "Unknown DateTime")
            dt_obj = datetime.datetime.strptime(run_date_time, "%Y-%m-%dT%H:%M:%S.%fZ")
            run_date = dt_obj.strftime("%d/%m/%Y")
            run_date2 = dt_obj.strftime("%d/%m")
            run_time = dt_obj.strftime("%H:%M")
            team_type = diff_to_type(data.get("difficulty", "Unknown Difficulty"))
            raid_type = loot_to_type(data.get("loot", "Unknown Loot Type"))
            gold_collector_discord_id = data.get("goldCollector", "Unknown GC")

            async for message in ctx.channel.history(limit=1000):
                if message.author.id == 579155972115660803:
                    mentions = re.findall(r"<@(\d+)>", message.content)

                    if mentions:
                        boosters = []
                        run_added = False
                        for mention in mentions:
                            if int(ctx.author.id) == int(mention):
                                add_run(
                                    run_id,
                                    actual_pot,
                                    mentions,
                                    run_date,
                                    run_time,
                                    team_type,
                                    raid_type,
                                    mention,
                                    gold_collector_discord_id,
                                )
                                run_added = True
                                boosters.append(f"{mention}:1:lead")
                            else:
                                boosters.append(f"{mention}:1:")
                        if not run_added:
                            add_run(
                                run_id,
                                actual_pot,
                                mentions,
                                run_date,
                                run_time,
                                team_type,
                                raid_type,
                                0,
                                gold_collector_discord_id,
                            )
                            run_added = True
                        boosters_str = ",".join(boosters)

                        output_message = f"```\n{run_date2}\n{run_time}\n{team_type}\n{raid_type}\n{actual_pot}\n{boosters_str}\n{gold_collector_discord_id}\n{run_id}\n```"
                        # await ctx.send(output_message)
                        if run_added:
                            await ctx.send("✅ Balance changed, you can check with .b")

                            # Create a list of mention names
                            mention_details = []
                            for mention in mentions:
                                user = await ctx.guild.fetch_member(int(mention))
                                if user:
                                    mention_details.append(
                                        f"{user.id} - {user.mention}"
                                    )
                                else:
                                    mention_details.append(
                                        f"{mention} - (Unknown User)"
                                    )

                            mention_message = "\n".join(mention_details)
                            if ctx.author.id != DISCORD_ID:
                                await ctx.author.send(
                                    f"**Mentioned Users:**\n{mention_message}\n**ATD for https://discord.com/channels/1129393746123964476/1231972793139331246:**\n{output_message}"
                                )

                            # Send DM to you (always)
                            owner = await ctx.bot.fetch_user(DISCORD_ID)
                            if owner:
                                await owner.send(
                                    f"**Mentioned Users:**\n{mention_message}\n**Invoked by:** {ctx.author.display_name}\n**ATD for https://discord.com/channels/1129393746123964476/1231972793139331246:**\n{output_message}"
                                )

                    else:
                        await ctx.send(
                            f"No mentions found in the latest message from {message.author.mention}."
                        )
                    break
            else:
                await ctx.send(f"No messages found from {message.author.mention}.")

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            print(e)

        finally:
            driver.quit()


async def setup(bot):
    await bot.add_cog(RaidLeader(bot))
