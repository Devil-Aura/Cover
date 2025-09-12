const { Telegraf } = require("telegraf");

// ========================
// CONFIG
// ========================
const BOT_TOKEN = "";
const bot = new Telegraf(BOT_TOKEN);

// In-memory database (use Mongo/SQLite for real app)
const userCovers = {};

// ========================
// COMMANDS
// ========================
bot.start((ctx) => ctx.reply("👋 Send me a photo to set as your cover, then send a video!"));

bot.command("show_cover", (ctx) => {
  const cover = userCovers[ctx.from.id];
  if (cover) {
    ctx.replyWithPhoto(cover, { caption: "📸 Your Current Cover" });
  } else {
    ctx.reply("❌ You don't have any cover set.");
  }
});

bot.command("del_cover", (ctx) => {
  delete userCovers[ctx.from.id];
  ctx.reply("🗑️ Your cover deleted.");
});

// ========================
// MEDIA HANDLERS
// ========================
bot.on("photo", async (ctx) => {
  const photos = ctx.message.photo;
  const fileId = photos[photos.length - 1].file_id; // best quality
  userCovers[ctx.from.id] = fileId;
  await ctx.reply("✅ Your new cover saved!");
});

bot.on("video", async (ctx) => {
  const cover = userCovers[ctx.from.id];
  if (!cover) return ctx.reply("❌ No cover set. Send an image first!");

  const video = ctx.message.video;
  const caption = ctx.message.caption || "";

  try {
    await ctx.telegram.sendVideo(ctx.chat.id, video.file_id, {
      caption: caption,
      thumb: cover, // 👈 thumbnail apply here
    });
  } catch (e) {
    console.error(e);
    await ctx.reply("⚠️ Failed to apply cover.");
  }
});

// ========================
// START BOT
// ========================
bot.launch().then(() => console.log("✅ Bot running..."));

// Enable graceful stop
process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));
