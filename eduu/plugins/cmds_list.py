from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from ..config import prefix
from ..utils import commands
from ..utils.localization import use_chat_lang


def gen_categories_kb(strings_manager):
    kb = []
    categories = list(commands.commands)
    while categories:
        name = strings_manager(categories[0], context="cmds_list")
        a = [InlineKeyboardButton(name, callback_data="view_category " + categories[0])]
        categories.pop(0)
        if categories:
            name = strings_manager(categories[0], context="cmds_list")
            a.append(
                InlineKeyboardButton(
                    name, callback_data="view_category " + categories[0]
                )
            )
            categories.pop(0)
        kb.append(a)
    return kb


@Client.on_callback_query(filters.regex("^commands$"))
@use_chat_lang()
async def cmds_list(c: Client, m: CallbackQuery, strings):
    await m.answer(strings("list_commands_panel"))
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            *gen_categories_kb(strings),
            [
                InlineKeyboardButton(
                    strings("back_btn", context="general"), callback_data="start_back"
                )
            ],
        ]
    )
    await m.message.edit_text(strings("select_command_category"), reply_markup=keyboard)


@Client.on_message(filters.command(["help", "config"], prefix))
@use_chat_lang()
async def show_help(c: Client, m: Message, strings):
    if m.chat.type == ChatType.PRIVATE:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                *gen_categories_kb(strings),
                [
                    InlineKeyboardButton(
                        strings("back_btn", context="general"),
                        callback_data="start_back",
                    )
                ],
            ]
        )
        await m.reply_text(strings("select_command_category"), reply_markup=keyboard)
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        strings("start_chat", context="start"),
                        url=f"https://t.me/{c.me.username}?start=help",
                    )
                ]
            ]
        )
        await m.reply_text(strings("group_help"), reply_markup=keyboard)


@Client.on_callback_query(filters.regex("^view_category .+"))
@use_chat_lang()
async def get_category(c: Client, m: CallbackQuery, strings):
    await m.answer("available commands")
    msg = commands.get_commands_message(strings, m.data.split(maxsplit=1)[1])
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    strings("back_btn", context="general"), callback_data="commands"
                )
            ]
        ]
    )
    await m.message.edit_text(msg, reply_markup=keyboard)
