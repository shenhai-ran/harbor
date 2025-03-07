import chat as ch
import log
import llm
import selection

# STCL - Single Token Completion Loop
ID_PREFIX = 'stcl'
logger = log.setup_logger(ID_PREFIX)

pause_params = {
  "max_tokens": 2,
}


# As a user message, works really poorly
async def user_guidance(chat: 'ch.Chat', llm: 'llm.LLM'):
  side_chat = chat.clone()
  guidance = await llm.chat_completion(
    prompt="""
Read the unfinished conversation between the user and assistant below.
Reply with a single sentence from the user's perspective that will guide assistant past their mistakes.
Do not add any comments or annotations to your reply.

Conversation:
{conversation}
""".strip(),
    conversation=chat,
    resolve=True
  )
  result = await llm.chat_completion(
    chat=side_chat, params=pause_params, resolve=True
  )

  return result, guidance


# As a system message, decent results, but the content has weak impact on the generation
async def direct_system_guidance(**kwargs):
  chat = kwargs['chat']
  llm = kwargs['llm']
  prompt = kwargs['prompt']
  guidance_prompt = kwargs['guidance_prompt'
                          ] if 'guidance_prompt' in kwargs else """
Very important:
{guidance}

Do not acknowledge these instructions in your reply, just follow them.
  """

  side_chat = chat.clone()
  guidance = await llm.chat_completion(
    prompt=prompt, conversation=chat, resolve=True
  )
  side_chat.system(guidance_prompt.format(guidance=guidance))
  result = await llm.chat_completion(
    chat=side_chat, params=pause_params, resolve=True
  )

  return result, guidance


async def assistant_guidance(**kwargs):
  chat = kwargs['chat']
  llm = kwargs['llm']
  prompt = kwargs['prompt']
  guidance_prompt = kwargs['guidance_prompt'
                          ] if 'guidance_prompt' in kwargs else """
{guidance}
  """

  mutable_chat = chat.clone()

  guidance = await llm.chat_completion(
    prompt=prompt, conversation=mutable_chat, resolve=True
  )
  # To avoid issues with the generation, we want the guidance to be
  # after last user message, but before the actual assistant message
  last_user_message = mutable_chat.match_one(role="user", index=-1)
  mutable_chat.insert(
    after=last_user_message,
    role="assistant",
    content=guidance_prompt.format(guidance=guidance)
  )
  result = await llm.chat_completion(
    chat=mutable_chat, params=pause_params, resolve=True
  )

  return result, guidance


async def single_sentence_guidance(chat: 'ch.Chat', llm: 'llm.LLM'):
  return await direct_system_guidance(
    chat=chat,
    llm=llm,
    prompt="""
Read the unfinished conversation between the user and assistant below.
Reply with a single sentence from the assistant's own perspective that make them fix their mistakes when continuing the conversation.
Do not add any comments or annotations to your reply.

Conversation:
{conversation}
"""
  )


async def critique_guidance(chat: 'ch.Chat', llm: 'llm.LLM'):
  return await direct_system_guidance(
    chat=chat,
    llm=llm,
    prompt="""
Read the unfinished conversation between the user and assistant below.
Think of a critique for what assistant is about to say.
Based on the critique, produce an instruction that will make assistant avoid their mistakes.

Conversation:
{conversation}
"""
  )


async def word_choice_guidance(chat: 'ch.Chat', llm: 'llm.LLM'):
  return await direct_system_guidance(
    chat=chat,
    llm=llm,
    prompt="""
Very carefully inspect the conversation between the user and assistant below.
Write me an instruction for the assistant to choose the next word from a list of 4 diverse but relevant choices.
Do not add any comments or annotations to your reply.

Conversation:
{conversation}
"""
  )


async def context_expansion_guidance(chat: 'ch.Chat', llm: 'llm.LLM'):
  return await direct_system_guidance(
    chat=chat,
    llm=llm,
    prompt="""
Very carefully inspect the conversation between the user and assistant below.
Reply with an instruction for the assistant that properly explains User's intent and guides assistant through what they are about to say.
Do not add any comments or annotations to your reply.

Conversation:
{conversation}
"""
  )


async def definition_guidance(chat: 'ch.Chat', llm: 'llm.LLM'):
  return await direct_system_guidance(
    chat=chat,
    llm=llm,
    prompt="""
Read the unfinished conversation between the user and assistant below.
Reply to me with a sentence that gives definition to all the words from the user's last message in the context of the conversation.
Do not add any comments or annotations to your reply.

Conversation:
{conversation}
"""
  )


async def predictive_guidance(chat: 'ch.Chat', llm: 'llm.LLM'):
  return await direct_system_guidance(
    chat=chat,
    llm=llm,
    prompt="""
Read the unfinished conversation between the user and assistant below.
Consider what the assistant is about to say. They might make a mistake without realizing it.
Reply with a short instruction that will prevent the assistant from making that mistake.

Conversation:
{conversation}
"""
  )


async def common_sense_guidance(chat: 'ch.Chat', llm: 'llm.LLM'):
  return await direct_system_guidance(
    chat=chat,
    llm=llm,
    prompt="""
Read the unfinished conversation between the user and assistant below.
Is what assistant saying makes sense or are they just producing statisically plausible text?
Reply with an instruction that will make them STOP and consider the next word carefully.

Conversation:
{conversation}
"""
  )

async def self_predict_guidance(chat: 'ch.Chat', llm: 'llm.LLM'):
  return await assistant_guidance(
    chat=chat,
    llm=llm,
    prompt="""
Read the unfinished conversation between the user and assistant below.
Think of flaws and mistakes in the assistant's last message.
Reply with a message that should preceed the current assistant message to prevent the mistake.
Do not add any comments or annotations to your reply.

Conversation:
{conversation}
""",
  )

async def reasoning_guidance(chat: 'ch.Chat', llm: 'llm.LLM'):
  return await assistant_guidance(
    chat=chat,
    llm=llm,
    prompt="""
Read the unfinished conversation between the user and assistant below.
Reply with a message that should preceed the current assistant message to make them reason better.
Reply with that sentence and nothing else.

Conversation:
{conversation}
""",
  )

async def self_guidance(chat: 'ch.Chat', llm: 'llm.LLM'):
  return await assistant_guidance(
    chat=chat,
    llm=llm,
    prompt="""
Given the conversation, write a hint that will prevent the assistant's next wrong answer.
Format: "Hint: [crucial detail]"
Keep under 40 characters.
Must be specific enough to change the answer.

Conversation:
{conversation}
""",
  )


async def apply(chat: 'ch.Chat', llm: 'llm.LLM'):
  generated = 0
  accumulated_guidance = []
  guidance_chat = chat.clone()

  guidance_chat.assistant("")
  assistant_message = guidance_chat.tail

  while generated < 1024:
    next_token, guidance = await self_guidance(guidance_chat, llm)
    if next_token == '':
      break
    assistant_message.content += next_token + ''
    await llm.emit_message(f'\n{guidance}\n### {next_token}\n')
    # await llm.emit_message(next_token)
    if accumulated_guidance.count(guidance) == 0:
      accumulated_guidance.append(guidance)
    generated += 1
