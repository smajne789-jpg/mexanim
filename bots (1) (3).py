    save_last_classic_result(current_message_id, current_prize, classic_participants, winners)
    classic_message_id = None
    classic_participants = []
    classic_prize = ""

    await callback.answer("Розыгрыш завершен")
    await callback.message.answer("✅ Обычный розыгрыш завершен. Рерол доступен из админ-панели.", reply_markup=admin_keyboard())


@dp.callback_query_handler(lambda c: c.data == "delete_classic_v2")
async def delete_classic_v2(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    if not classic_message_id:
        await callback.answer("Обычный розыгрыш не активен", show_alert=True)
        return

    await delete_classic_giveaway()
    await callback.answer("Обычный розыгрыш удален")
    await callback.message.answer("✅ Обычный розыгрыш удален.", reply_markup=admin_keyboard())


@dp.callback_query_handler(lambda c: c.data == "classic_reroll_menu")
async def classic_reroll_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    if not last_classic_message_id or not last_classic_winners:
        await callback.answer("Нет завершенного большого розыгрыша для рерола", show_alert=True)
        return

    await callback.message.answer(
        "🎲 Выбери победителя, которого нужно рерольнуть:",
        reply_markup=classic_reroll_keyboard(),
    )
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("classic_reroll_pick:"))
async def classic_reroll_pick(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    if not last_classic_message_id or not last_classic_winners:
        await callback.answer("Рерол недоступен", show_alert=True)
        return

    try:
        winner_index = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer("Не удалось определить победителя", show_alert=True)
        return

    if winner_index < 0 or winner_index >= len(last_classic_winners):
        await callback.answer("Такого победителя нет", show_alert=True)
        return

    current_winner = last_classic_winners[winner_index]
    busy_ids = {
        winner["id"]
        for index, winner in enumerate(last_classic_winners)
        if index != winner_index
    }
    candidate_pool = [
        participant
        for participant in last_classic_participants
        if participant["id"] not in busy_ids and participant["id"] != current_winner["id"]
    ]

    if not candidate_pool:
        await callback.answer("Нет свободных участников для замены", show_alert=True)
        return

    new_winner = random.choice(candidate_pool).copy()
    last_classic_winners[winner_index] = new_winner

    await bot.edit_message_caption(
        chat_id=CHANNEL_ID,
        message_id=last_classic_message_id,
        caption=classic_result_caption(last_classic_prize, last_classic_winners),
        reply_markup=None,
    )

    await callback.answer("Рерол выполнен")
    await callback.message.answer(
        f"🎲 Рерол выполнен.\nБыло: {user_display(current_winner)}\nСтало: {user_display(new_winner)}",
        reply_markup=admin_keyboard(),
    )


@dp.callback_query_handler(lambda c: c.data == "finish_duel_v2")
async def finish_duel_v2(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    ok, text = await finish_duel_giveaway()
    await callback.answer(text, show_alert=not ok)
    await callback.message.answer(text, reply_markup=admin_keyboard())


@dp.callback_query_handler(lambda c: c.data == "delete_duel_v2")
async def delete_duel_v2(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    if not duel_message_id:
        await callback.answer("Дуэль не активна", show_alert=True)
        return

    await delete_duel_giveaway()
    await callback.answer("Дуэль удалена")
    await callback.message.answer("✅ Дуэль удалена.", reply_markup=admin_keyboard())


@dp.message_handler(content_types=types.ContentType.NEW_CHAT_MEMBERS)
async def track_referral_join_message(message: types.Message):
    if not referral_chat_matches(message.chat):
        return

    invite_link = getattr(message, "invite_link", None)
    for user in message.new_chat_members:
        await register_referral_join(user, invite_link)


if hasattr(dp, "chat_member_handler"):
    @dp.chat_member_handler()
    async def track_referral_chat_member(update):
        if not referral_chat_matches(update.chat):
            return

        old_status = getattr(update.old_chat_member, "status", None)
        new_status = getattr(update.new_chat_member, "status", None)
        joined_from_outside = old_status in {"left", "kicked"} and new_status in {
            "member",
            "restricted",
            "administrator",
            "creator",
        }

        if joined_from_outside:
            await register_referral_join(update.new_chat_member.user, getattr(update, "invite_link", None))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(
        dp,
        skip_updates=True,
        allowed_updates=["message", "callback_query", "chat_member"],
    )
