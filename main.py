import logging
import datetime
import json

import telebot
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ConversationHandler
from telegram import ReplyKeyboardMarkup
from scripts.__all_models import User, Questions
from scripts.env import BOT_TOKEN, reply_keyboard
from scripts import db_session
from scripts.logger_filter import MaxLevelFilter, ExceptionFormatter

logger = logging.getLogger(__name__)

general_handler = logging.FileHandler('db/log_file.txt')
general_handler.setLevel(logging.WARNING)
general_handler.addFilter(MaxLevelFilter(logging.WARNING))
general_formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
general_handler.setFormatter(general_formatter)

exception_handler = logging.FileHandler('db/logged_errors_file.txt')
exception_handler.setLevel(logging.ERROR)
formatter = ExceptionFormatter()
exception_handler.setFormatter(formatter)

logger.addHandler(general_handler)
logger.addHandler(exception_handler)

db_session.global_init('db/site.db')
mode = 'u'
current_question = Questions()
current_answers = []


# noinspection PyUnusedLocal
async def echo(update, context):
    await update.message.reply_text(f'{update.message.text}', reply_markup=markup)


# noinspection PyUnusedLocal
async def start(update, context):
    try:
        logger.warning(f'          App started            : {update.effective_user.id} : {update.effective_user.name}')

        global mode
        global markup

        user_registrarion(update.effective_user)
        user = update.effective_user
        db_sess = db_session.create_session()

        if db_sess.query(User).filter(User.telegram_id.like(user.id)).first().type == 'Unregistered':
            mode = 'u'
            application.add_handler(CommandHandler("register", register))
        elif db_sess.query(User).filter(User.telegram_id.like(user.id)).first().type == 'Registered':
            application.add_handler(questionaire_handler)
            application.add_handler(question_adding_handler)
            mode = 'r'
        elif db_sess.query(User).filter(User.telegram_id.like(user.id)).first().type == 'Moderator':
            application.add_handler(questionaire_handler)
            application.add_handler(question_adding_handler)
            application.add_handler(moderator_handler)
            mode = 'm'
            with open('db/moderator_question_relation.json') as file:
                data = json.load(file)
                if not str(user.id) in data:
                    data[str(user.id)] = []
            with open('db/moderator_question_relation.json', 'w') as file:
                json.dump(data, file)
        markup = ReplyKeyboardMarkup(reply_keyboard[mode], one_time_keyboard=False)

        await update.message.reply_html(f"Welcome {user.mention_html()}. I am QuestionMark.", reply_markup=markup)
    except Exception as exc:
        logger.warning(f'          ERROR OCCURED          : {update.effective_user.id} : {update.effective_user.name}')
        logger.error(f'Logging exception on {datetime.datetime.now()} found by {update.effective_user.name} - {update.effective_user.id}', exc_info=True)
        await update.message.reply_text(f'We apologise, something went wrong. :(\nError type: {exc.__class__}')


# noinspection PyUnusedLocal
async def help_command(update, context):
    logger.warning(f'       Help Command called       : {update.effective_user.id} : {update.effective_user.name}')

    text = ['Welcome to telegram bot QuestionMark. This bot was created for not only entertaining, but also serious needs. For example, you can use this bot to collect statistics of people`s opinion on various topics. The idea of the project is that it allows you to create short questions with several answers, and users can answer them and see how other users answered. For this purpose, statistics is kept on questions, as well as there are likes and dislikes. To prevent bad questions, reports are implemented, thanks to which the community can tell moderators to remove the question.', '', 'Command list:']
    db_sess = db_session.create_session()
    text.append('/start - Starting / Restarting the bot.')
    text.append('/help - Bot commands + dev contacts.')
    if db_sess.query(User).filter(User.telegram_id.like(update.effective_user.id)).first().type == 'Unregistered':
        text.append('/register - Registration in the system. Requires channel subscription.')
    elif db_sess.query(User).filter(User.telegram_id.like(update.effective_user.id)).first().type == 'Registered':
        text.append('/get_question  - Calls a question for you, bot will guide you how to answer and will show current statistics on this question.')
        text.append('/add_question - Allows to create your own question. Bot will guide you through creation.')
        text += ['', '']
    if db_sess.query(User).filter(User.telegram_id.like(update.effective_user.id)).first().type == 'Moderator':
        text.append(
            '/get_question  - Calls a question for you, bot will guide you how to answer and will show current statistics on this question.')
        text.append('/add_question - Allows to create your own question. Bot will guide you through creation.')
        text.append('/moderate - Special function for mods, allowing to moderate certain question by either suspending the author and deleting it or sparing the author.')
    db_sess.close()
    text.append('\n' + 'Share your questions, answer them and have fun! :)')
    text.append('Dev contacts: <a href="tg://user?id=5833077979">DrAeyJ</a>')
    await update.message.reply_text('\n'.join(text), reply_markup=markup, parse_mode='HTML')


# noinspection PyUnusedLocal
def user_registrarion(tg_user):
    db_sess = db_session.create_session()

    ids = [i.telegram_id for i in db_sess.query(User).all()]

    if tg_user.id not in ids:
        with open('db/user_question_relation.json', encoding='utf-8') as file:
            data = json.load(file)
            data[tg_user.id] = []
        with open('db/user_question_relation.json', 'w', encoding='utf-8') as file:
            json.dump(data, file)
        user = User()
        user.name = tg_user.name
        user.telegram_id = tg_user.id
        db_sess = db_session.create_session()
        db_sess.add(user)
        db_sess.commit()
        print(f'Registered TG user: {tg_user.id}')

    db_sess.close()


# noinspection PyUnusedLocal
async def get_random_questions(update, context):
    try:
        db_sess = db_session.create_session()
        if datetime.datetime.now() >= db_sess.query(User).filter(
                User.telegram_id.like(update.effective_user.id)).first().suspended_until:
            logger.warning(f'        Question called          : {update.effective_user.id} : {update.effective_user.name}')

            global current_question
            global current_answers

            if db_sess.query(Questions).all():
                questions = db_sess.query(Questions).all()
                with open('db/user_question_relation.json') as file:
                    try:
                        data = json.load(file)
                    except json.decoder.JSONDecodeError:
                        data = {}
                    question = None
                    for i in questions:
                        if i.id in data[str(update.effective_user.id)]:
                            continue
                        else:
                            question = i
                            break
                    if not question:
                        await update.message.reply_text(
                            'Sorry, no questions are available at the moment, or you already answered each one.')
                        return ConversationHandler.END
                current_question = question
                author_name = db_sess.query(User).filter(User.telegram_id.like(question.author_tg_id)).first().name
                answers = [question.answer_1,
                           question.answer_2,
                           question.answer_3,
                           question.answer_4]
                answer_sheet = []
                emote = '1️⃣'[1:]
                for i in range(len(answers)):
                    if answers[i] is not None:
                        answer_sheet.append(f'{str(i + 1) + emote}: {answers[i]}')
                current_answers = answer_sheet
                answer_sheet = '\n'.join(answer_sheet)

                question_repr = [
                    f'Author: {author_name}                             ',
                    '',
                    f'Content: {question.content}',
                    '',
                    f'Answers: \n{answer_sheet}'
                ]
                question_repr = '\n'.join(question_repr)

                keyboard = [['1️⃣', '2️⃣']]
                if len(answer_sheet.split('\n')) == 3:
                    keyboard.append(['3️⃣'])
                elif len(answer_sheet.split('\n')) == 4:
                    keyboard.append(['3️⃣', '4️⃣'])
                keyboard.append(['/skip', '/stop'])

                if question:
                    await update.message.reply_text(question_repr,
                                                    reply_markup=ReplyKeyboardMarkup(keyboard,
                                                                                     one_time_keyboard=True))
                    return 1
            else:
                await update.message.reply_text(
                    'Sorry, no questions are available at the moment, or you already answered each one.')
                return ConversationHandler.END
        else:
            await update.message.reply_text(
                f'You seem to be currently suspended from any activity in our app. \nYou are suspended until {db_sess.query(User).filter(User.telegram_id.like(update.effective_user.id)).first().suspended_until}',
                reply_markup=ReplyKeyboardMarkup(reply_keyboard[mode]))
            return ConversationHandler.END

        db_sess.close()
    except Exception as exc:
        logger.warning(f'          ERROR OCCURED          : {update.effective_user.id} : {update.effective_user.name}')
        logger.error(f'Logging exception on {datetime.datetime.now()} found by {update.effective_user.name} - {update.effective_user.id}', exc_info=True)
        await update.message.reply_text(f'We apologise, something went wrong. :(\nError type: {exc.__class__}', reply_markup=markup)
        return ConversationHandler.END


# noinspection PyUnusedLocal
async def stats(update, context):
    global markup

    try:
        global current_question
        global current_answers

        if int(update.message.text[0]) in list(range(1, len(current_answers) + 1)):
            answers = [current_question.answer_1_count,
                       current_question.answer_2_count,
                       current_question.answer_3_count,
                       current_question.answer_4_count]
            ans = []
            for i in range(len(answers)):
                if answers[i] is not None:
                    ans.append(answers[i])
            ans1 = []
            emote = '1️⃣'[1:]
            for i in range(len(ans)):
                try:
                    ans1.append(f'{str(i + 1) + emote}: {round(ans[i] / sum(ans) * 100)}%')
                except ZeroDivisionError:
                    ans1.append(f'{str(i + 1) + emote}: 0%')
            ans1 = '\n'.join(ans1)
            answer_repr = [
                f'Your answer: {update.message.text}                             ',
                '',
                f'Answer precentage: \n{ans1}',
                '',
                f'Likes: {current_question.likes_count}',
                f'Dislikes: {current_question.dislikes_count}',
                f'Reports: {current_question.reports_count}',
                '',
                f'Share your opinion about this question:\nUse like, dislike or report.'
            ]
            answer_repr = '\n'.join(answer_repr)

            if update.message.text[0] == '1':
                db_sess = db_session.create_session()
                db_sess.query(Questions).filter(Questions.id.like(current_question.id)).first().answer_1_count += 1
                db_sess.commit()
                db_sess.close()
            elif update.message.text[0] == '2':
                db_sess = db_session.create_session()
                db_sess.query(Questions).filter(Questions.id.like(current_question.id)).first().answer_2_count += 1
                db_sess.commit()
                db_sess.close()
            elif update.message.text[0] == '3':
                db_sess = db_session.create_session()
                db_sess.query(Questions).filter(Questions.id.like(current_question.id)).first().answer_3_count += 1
                db_sess.commit()
                db_sess.close()
            elif update.message.text[0] == '4':
                db_sess = db_session.create_session()
                db_sess.query(Questions).filter(Questions.id.like(current_question.id)).first().answer_4_count += 1
                db_sess.commit()
                db_sess.close()

            await update.message.reply_text(answer_repr, reply_markup=ReplyKeyboardMarkup(reply_keyboard['l-d-r']))
            return 2
        else:
            keyboard = [['1️⃣', '2️⃣']]
            if len(current_answers) == 3:
                keyboard.append(['3️⃣'])
            elif len(current_answers) == 4:
                keyboard.append(['3️⃣', '4️⃣'])

            await update.message.reply_text('Invalid answer. Please, type in a valid answer.',
                                            reply_markup=ReplyKeyboardMarkup(keyboard,
                                                                             one_time_keyboard=True))
            return 1
    except Exception as exc:
        logger.warning(f'          ERROR OCCURED          : {update.effective_user.id} : {update.effective_user.name}')
        logger.error(f'Logging exception on {datetime.datetime.now()} found by {update.effective_user.name} - {update.effective_user.id}', exc_info=True)
        await update.message.reply_text(f'We apologise, something went wrong. :(\nError type: {exc.__class__}', reply_markup=markup)
        return ConversationHandler.END


# noinspection PyUnusedLocal
async def like_dislike_report(update, context):
    try:
        global current_question
        if update.message.text == 'Like':
            db_sess = db_session.create_session()
            db_sess.query(Questions).filter(Questions.id.like(current_question.id)).first().likes_count += 1
            db_sess.commit()
            db_sess.close()
            await update.message.reply_text('Question liked. \nYaay! :)', reply_markup=markup)
        elif update.message.text == 'Dislike':
            db_sess = db_session.create_session()
            db_sess.query(Questions).filter(Questions.id.like(current_question.id)).first().dislikes_count += 1
            db_sess.commit()
            db_sess.close()
            await update.message.reply_text('Question disliked. \nAww :(', reply_markup=markup)
        elif update.message.text == 'Report':
            db_sess = db_session.create_session()
            db_sess.query(Questions).filter(Questions.id.like(current_question.id)).first().reports_count += 1
            db_sess.commit()
            db_sess.close()
            await update.message.reply_text('Report posted. Thank you for feedback! :)', reply_markup=markup)
        else:
            await update.message.reply_text('Reaction skipped. o_o', reply_markup=markup)
        with open('db/user_question_relation.json') as file:
            data = json.load(file)
            data[str(update.effective_user.id)].append(current_question.id)
        with open('db/user_question_relation.json', 'w') as file:
            json.dump(data, file)
        current_question = Questions()
        return ConversationHandler.END
    except Exception as exc:
        logger.warning(f'          ERROR OCCURED          : {update.effective_user.id} : {update.effective_user.name}')
        logger.error(f'Logging exception on {datetime.datetime.now()} found by {update.effective_user.name} - {update.effective_user.id}', exc_info=True)
        await update.message.reply_text(f'We apologise, something went wrong. :(\nError type: {exc.__class__}', ReplyKeyboardMarkup=markup)
        return ConversationHandler.END


# noinspection PyUnusedLocal
async def stop(update, context):
    logger.warning(f'        Proccess stopped         : {update.effective_user.id} : {update.effective_user.name}')

    global markup
    global question_in_creation

    markup = ReplyKeyboardMarkup(reply_keyboard[mode], one_time_keyboard=False)
    question_in_creation = Questions()
    await update.message.reply_text('Ended.', reply_markup=markup)
    return ConversationHandler.END


# noinspection PyUnusedLocal
async def skip(update, context):
    logger.warning(f'        Question skipped         : {update.effective_user.id} : {update.effective_user.name}')

    global current_question
    global markup

    with open('db/user_question_relation.json') as file:
        data = json.load(file)
        data[str(update.effective_user.id)].append(current_question.id)
    with open('db/user_question_relation.json', 'w') as file:
        json.dump(data, file)
    current_question = Questions()

    await update.message.reply_text('Question skiiped. o_o', reply_markup=markup)
    return ConversationHandler.END


def check_subscription(user_id, channel_id):
    bot = telebot.TeleBot(BOT_TOKEN)
    status = bot.get_chat_member(channel_id, user_id).status
    return status in ['member', 'administrator', 'creator']


# noinspection PyUnusedLocal
async def register(update, context):
    try:
        global mode
        global markup

        if check_subscription(update.effective_user.id, '@QuestionareAd') is True:
            mode = 'r'
            markup = ReplyKeyboardMarkup(reply_keyboard[mode], one_time_keyboard=False)
            db_sess = db_session.create_session()
            db_sess.query(User).filter(User.telegram_id.like(update.effective_user.id)).first().type = 'Registered'
            db_sess.commit()
            db_sess.close()
            application.add_handler(questionaire_handler)
            application.add_handler(question_adding_handler)
            await update.message.reply_text('User type changed to: Registered.', reply_markup=markup)

            logger.warning(f' USER TYPE CHANGED TO REGISTERED : {update.effective_user.id} : {update.effective_user.name}')

        else:
            await update.message.reply_text('You seem not to be subscribed to the channel <a href="https://t.me/QuestionareAd">QuestionMark`s Advertising</a>. \nWhy don`t you go and do that? ;)', reply_markup=markup, parse_mode='HTML')
    except Exception as exc:
        logger.warning(f'          ERROR OCCURED          : {update.effective_user.id} : {update.effective_user.name}')
        logger.error(f'Logging exception on {datetime.datetime.now()} found by {update.effective_user.name} - {update.effective_user.id}', exc_info=True)
        await update.message.reply_text(f'We apologise, something went wrong. :(\nError type: {exc.__class__}')


question_in_creation = Questions()


# noinspection PyUnusedLocal
async def add_question(update, context):
    try:
        logger.warning(f' Question adding process started : {update.effective_user.id} : {update.effective_user.name}')

        global question_in_creation
        global markup

        db_sess = db_session.create_session()
        if datetime.datetime.now() >= db_sess.query(User).filter(
                User.telegram_id.like(update.effective_user.id)).first().suspended_until:
            markup = ReplyKeyboardMarkup(reply_keyboard['q-a'], one_time_keyboard=False)
            question_in_creation.author_tg_id = update.effective_user.id
            await update.message.reply_text('Please write the content of the question.', reply_markup=markup)
            return 1
        else:
            await update.message.reply_text(
                f'You seem to be currently suspended from any activity in our app. \nYou are suspended until {db_sess.query(User).filter(User.telegram_id.like(update.effective_user.id)).first().suspended_until}',
                reply_markup=ReplyKeyboardMarkup(reply_keyboard[mode]))
            return ConversationHandler.END
    except Exception as exc:
        logger.warning(f'          ERROR OCCURED          : {update.effective_user.id} : {update.effective_user.name}')
        logger.error(f'Logging exception on {datetime.datetime.now()} found by {update.effective_user.name} - {update.effective_user.id}', exc_info=True)
        await update.message.reply_text(f'We apologise, something went wrong. :(\nError type: {exc.__class__}')
        return ConversationHandler.END


# noinspection PyUnusedLocal
async def num_of_answers(update, context):
    global question_in_creation
    global markup

    question_in_creation.content = update.message.text
    await update.message.reply_text('How many answers does your question have?', reply_markup=markup)
    return 2


answers_left = 0


# noinspection PyUnusedLocal
async def answers_writing(update, context):
    global question_in_creation
    global answers_left
    global markup

    if answers_left:
        return 3

    try:
        if 2 <= int(update.message.text) <= 4:
            question_in_creation.answers_count = int(update.message.text)
            if int(update.message.text) >= 3:
                question_in_creation.answer_3_count = 0
            if int(update.message.text) == 4:
                question_in_creation.answer_4_count = 0
        else:
            await update.message.reply_text('How many answers does your question have?', reply_markup=markup)
            return 2
    except ValueError:
        await update.message.reply_text('How many answers does your question have?', reply_markup=markup)
        return 2
    answers_left = int(update.message.text)
    await update.message.reply_text('Please write the first answer to your question.', reply_markup=markup)
    return 3


# noinspection PyUnusedLocal
async def more_ans(update, context):
    try:
        global question_in_creation
        global answers_left
        global markup
        global mode

        if not question_in_creation.answer_1:
            question_in_creation.answer_1 = update.message.text
        elif not question_in_creation.answer_2:
            question_in_creation.answer_2 = update.message.text
        elif not question_in_creation.answer_3:
            question_in_creation.answer_3 = update.message.text
        elif not question_in_creation.answer_4:
            question_in_creation.answer_4 = update.message.text
        answers_left -= 1
        if not answers_left:
            logger.warning(f'         Question added          : {update.effective_user.id} : {update.effective_user.name}')

            markup = ReplyKeyboardMarkup(reply_keyboard[mode], one_time_keyboard=False)
            await update.message.reply_text(
                'Question added. \nPlease keep in mind that you will be suspended by the staff if your question is inappropriate.',
                reply_markup=markup)
            db_sess = db_session.create_session()
            db_sess.add(question_in_creation)
            db_sess.commit()
            db_sess.close()
            question_in_creation = Questions()
            return ConversationHandler.END
        else:
            await update.message.reply_text('Next answer please.', reply_markup=markup)
            return 3
    except Exception as exc:
        logger.warning(f'          ERROR OCCURED          : {update.effective_user.id} : {update.effective_user.name}')
        logger.error(f'Logging exception on {datetime.datetime.now()} found by {update.effective_user.name} - {update.effective_user.id}', exc_info=True)
        await update.message.reply_text(f'We apologise, something went wrong. :(\nError type: {exc.__class__}')
        return ConversationHandler.END


# noinspection PyUnusedLocal
async def moderate(update, context):
    try:
        db_sess = db_session.create_session()
        if datetime.datetime.now() >= db_sess.query(User).filter(
                User.telegram_id.like(update.effective_user.id)).first().suspended_until:
            logger.warning(f'       Moderation started        : {update.effective_user.id} : {update.effective_user.name}')

            global current_question
            global current_answers

            if db_sess.query(Questions).all():
                questions = db_sess.query(Questions).all()
                with open('db/moderator_question_relation.json') as file:
                    try:
                        data = json.load(file)
                    except json.decoder.JSONDecodeError:
                        data = {}
                    question = None
                    for i in questions:
                        if i.id in data[str(update.effective_user.id)]:
                            continue
                        else:
                            question = i
                            break
                if not question:
                    await update.message.reply_text('No questions to moderate right now.',
                                                    reply_markup=ReplyKeyboardMarkup(reply_keyboard[mode],
                                                                                     one_time_keyboard=False))
                    return ConversationHandler.END
                current_question = question
                author_name = db_sess.query(User).filter(User.telegram_id.like(question.author_tg_id)).first().name
                answers = [question.answer_1,
                           question.answer_2,
                           question.answer_3,
                           question.answer_4]
                answer_sheet = []
                emote = '1️⃣'[1:]
                for i in range(len(answers)):
                    if answers[i] is not None:
                        answer_sheet.append(f'{str(i + 1) + emote}: {answers[i]}')
                current_answers = answer_sheet
                answer_sheet = '\n'.join(answer_sheet)

                question_repr = [
                    f'Author: {author_name}                             ',
                    '',
                    f'Content: {question.content}',
                    '',
                    f'Answers: \n{answer_sheet}',
                    '',
                    f'Likes: {current_question.likes_count}',
                    f'Dislikes: {current_question.dislikes_count}',
                    f'Reports: {current_question.reports_count}',
                    '',
                    'You can either delete this question and suspend the author\nor skip it if you think that it`s fine to.'
                ]
                question_repr = '\n'.join(question_repr)
                await update.message.reply_text(question_repr, reply_markup=ReplyKeyboardMarkup(reply_keyboard['i-m'],
                                                                                                one_time_keyboard=False))
                return 1
            else:
                await update.message.reply_text('No questions to moderate right now.',
                                                reply_markup=ReplyKeyboardMarkup(reply_keyboard[mode], one_time_keyboard=False))
                db_sess.close()
                return ConversationHandler.END
        else:
            await update.message.reply_text(
                f'You seem to be currently suspended from any activity in our app. \nYou are suspended until {db_sess.query(User).filter(User.telegram_id.like(update.effective_user.id)).first().suspended_until}',
                reply_markup=ReplyKeyboardMarkup(reply_keyboard[mode], one_time_keyboard=False))
            db_sess.close()
            return ConversationHandler.END
    except Exception as exc:
        logger.warning(f'          ERROR OCCURED          : {update.effective_user.id} : {update.effective_user.name}')
        logger.error(f'Logging exception on {datetime.datetime.now()} found by {update.effective_user.name} - {update.effective_user.id}', exc_info=True)
        await update.message.reply_text(f'We apologise, something went wrong. :(\nError type: {exc.__class__}')
        return ConversationHandler.END


# noinspection PyUnusedLocal
async def del_or_skip(update, context):
    try:
        global mode

        db_sess = db_session.create_session()
        if update.message.text == 'Delete and suspend':
            db_sess.delete(current_question)
            db_sess.commit()
            db_sess.close()
            await update.message.reply_text('How much days would you like to suspend the user for?',
                                            reply_markup=ReplyKeyboardMarkup(reply_keyboard['q-a'],
                                                                             one_time_keyboard=False))
            return 2
        elif update.message.text == 'Spare and skip':
            logger.warning(f'     Question skipped by mod     : {update.effective_user.id} : {update.effective_user.name}')

            db_sess.query(Questions).filter(Questions.id.like(current_question.id)).first().reports_count = 0
            db_sess.commit()
            with open('db/moderator_question_relation.json') as file:
                data = json.load(file)
                data[str(update.effective_user.id)].append(current_question.id)
            with open('db/moderator_question_relation.json', 'w') as file:
                json.dump(data, file)
            db_sess.close()
            await update.message.reply_text('Thank you for the moderation! :)',
                                            reply_markup=ReplyKeyboardMarkup(reply_keyboard[mode], one_time_keyboard=False))
            return ConversationHandler.END
    except Exception as exc:
        logger.warning(f'          ERROR OCCURED          : {update.effective_user.id} : {update.effective_user.name}')
        logger.error(f'Logging exception on {datetime.datetime.now()} found by {update.effective_user.name} - {update.effective_user.id}', exc_info=True)
        await update.message.reply_text(f'We apologise, something went wrong. :(\nError type: {exc.__class__}')
        return ConversationHandler.END


# noinspection PyUnusedLocal
async def suspension_time(update, context):
    try:
        logger.warning(f'     Question deleted by mod     : {update.effective_user.id} : {update.effective_user.name}')

        try:
            time = int(update.message.text)
        except ValueError:
            await update.message.reply_text('How much days would you like to suspend the user for?')
            return 2
        db_sess = db_session.create_session()
        db_sess.query(User).filter(User.telegram_id.like(
            current_question.author_tg_id)).first().suspended_until = datetime.datetime.now() + datetime.timedelta(
            days=time)
        db_sess.commit()
        with open('db/user_question_relation.json') as file:
            data = json.load(file)
            for i in data:
                if current_question.id in data[i]:
                    data[i].remove(current_question.id)
        with open('db/user_question_relation.json', 'w') as file:
            json.dump(data, file)
        db_sess.close()
        await update.message.reply_text(
            f'Author of the question suspended for {time} days. \nThank you for your moderation.',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard[mode], one_time_keyboard=False))
        return ConversationHandler.END
    except Exception as exc:
        logger.warning(f'          ERROR OCCURED          : {update.effective_user.id} : {update.effective_user.name}')
        logger.error(f'Logging exception on {datetime.datetime.now()} found by {update.effective_user.name} - {update.effective_user.id}', exc_info=True)
        await update.message.reply_text(f'We apologise, something went wrong. :(\nError type: {exc.__class__}')
        return ConversationHandler.END


application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
questionaire_handler = ConversationHandler(
    entry_points=[CommandHandler('get_question', get_random_questions)],

    states={
        0: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_random_questions)],
        1: [MessageHandler(filters.TEXT & ~filters.COMMAND, stats)],
        2: [MessageHandler(filters.TEXT & ~filters.COMMAND, like_dislike_report)]
    },

    fallbacks=[CommandHandler('stop', stop), CommandHandler('skip', skip)])
question_adding_handler = ConversationHandler(
    entry_points=[CommandHandler('add_question', add_question)],

    states={
        1: [MessageHandler(filters.TEXT & ~filters.COMMAND, num_of_answers)],
        2: [MessageHandler(filters.TEXT & ~filters.COMMAND, answers_writing)],
        3: [MessageHandler(filters.TEXT & ~filters.COMMAND, more_ans)]
    },

    fallbacks=[CommandHandler('stop', stop)])
moderator_handler = ConversationHandler(
    entry_points=[CommandHandler('moderate', moderate)],

    states={
        1: [MessageHandler(filters.TEXT & ~filters.COMMAND, del_or_skip)],
        2: [MessageHandler(filters.TEXT & ~filters.COMMAND, suspension_time)]
    },

    fallbacks=[CommandHandler('stop', stop)])

markup = ReplyKeyboardMarkup(reply_keyboard[mode], one_time_keyboard=False)

application.run_polling()
