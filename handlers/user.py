import asyncio
from aiogram import F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, FSInputFile, ChatMemberLeft
)

from bot import dp, bot
from config import CHANNEL_ID

from models.dbs.orm import Orm
from models.dbs.models import *

from .callbacks import *
from .markups import *
from .states import *

@dp.message(Command('start'))
async def start_message_handler(message: Message, state: FSMContext):
    await state.clear()
    
    await Orm.create_user(message)
    await send_start_message(message)
    
async def send_start_message(message: Message):
    await bot.send_message(
        chat_id=message.from_user.id,
        text=await generate_start_text(message),
        reply_markup=await generate_channel_markup()
    )
    
@dp.callback_query(F.data == "check_sub")
async def check_sub_handler(callback: CallbackQuery):
    # await callback.message.answer(
    #     text=subscription_thank_you_message,
    #     reply_markup=send_phone_markup
    # )
    if await is_in_channel(CHANNEL_ID, callback.from_user.id):
        await callback.message.answer(
            text=subscription_thank_you_message,
            reply_markup=send_phone_markup
        )
    else:
        await callback.message.delete()
        await send_start_message(callback)
        
@dp.message(F.contact)
async def get_phone_number(message: Message, state: FSMContext):
    await Orm.update_user_phone_number(message)
    await message.answer(
        text=phone_number_confirmation_text,
        reply_markup=go_to_test_markup
    )
    
@dp.callback_query(F.data == "go_to_test")
async def go_to_test_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        text=start_test_text
    )
    await asyncio.sleep(5)
    
    await state.update_data(current_question=1, answers={})
    await ask_question(callback.from_user.id, await state.get_data())

# Задать вопрос
async def ask_question(user_id, data):
    current_question = data['current_question']
    question_data = test_questions_and_answers.get(current_question)

    if question_data:
        question_text = f"<b>{question_data['question']}</b>"
        question_text += '\n\n' + '\n\n'.join(question_data['answers'].values())

        await bot.send_message(
            chat_id=user_id,
            text=question_text,
            reply_markup=answers_keyboard,
            parse_mode='HTML'
        )
    else:
        await finish_test(user_id, data)
        
async def finish_test(user_id, data):
    user_result = results[calculate_result(data['answers'])]
    await bot.send_message(
        chat_id=user_id,
        text=user_result
    )
    
    await asyncio.sleep(5)
    
    await bot.send_message(
        chat_id=user_id,
        text=ending_text,
        reply_markup=ending_markup
    )
    
    
def calculate_result(answers):
    result = {
        'A': 0,
        'B': 0,
        'C': 0,
        'D': 0
    }
    
    for answer in answers.values():
        result[answer] += 1
        
    return max(result, key=result.get)

@dp.callback_query(lambda callback: callback.data.startswith(('A.', 'B.', 'C.', 'D.')))
async def process_answer(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete_reply_markup()
    user_id = callback.from_user.id
    data = await state.get_data()
    current_question = data['current_question']
    answers = data['answers']
    
    answers[current_question] = callback.data[0]
    await state.update_data(answers=answers)
    
    await state.update_data(current_question=current_question + 1)
    await ask_question(user_id, await state.get_data())
    
async def is_in_channel(channel_id, telegram_id):
    member = await bot.get_chat_member(chat_id=channel_id, user_id=telegram_id)
    return type(member) != ChatMemberLeft





# @dp.message()
# async def get_channel_id(message: Message):
#     await message.answer(
#         text=f'<code>{message.forward_from_chat.id}</code>',
#         parse_mode='HTML'
#     )
    