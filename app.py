#!/usr/bin/env python
# -*- coding:utf-8 _*-
"""
@author:quincy qiang
@license: Apache Licence
@file: app.py
@time: 2024/05/21
@contact: yanqiangmiffy@gamil.com
"""
import os
import shutil
import gradio as gr
from gomate.applications.rag import RagApplication


# 修改成自己的配置！！！
class ApplicationConfig:
    llm_model_name = '/data/users/searchgpt/pretrained_models/chatglm3-6b'  # 本地模型文件 or huggingface远程仓库
    embedding_model_name = '/data/users/searchgpt/pretrained_models/bge-reranker-large'  # 检索模型文件 or huggingface远程仓库
    vector_store_path = './storage'
    docs_path = './data/docs'


config = ApplicationConfig()
application = RagApplication(config)
application.init_vector_store()


def get_file_list():
    if not os.path.exists("./docs"):
        return []
    return [f for f in os.listdir("./docs")]


file_list = get_file_list()


def upload_file(file):
    cache_base_dir = './docs/'
    if not os.path.exists(cache_base_dir):
        os.mkdir(cache_base_dir)
    filename = os.path.basename(file.name)
    shutil.move(file.name, cache_base_dir + filename)
    # file_list首位插入新上传的文件
    file_list.insert(0, filename)
    application.add_document("./docs/" + filename)
    return gr.Dropdown.update(choices=file_list, value=filename)


def set_knowledge(kg_name, history):
    try:
        application.load_vector_store()
        msg_status = f'{kg_name}知识库已成功加载'
    except Exception as e:
        print(e)
        msg_status = f'{kg_name}知识库未成功加载'
    return history + [[None, msg_status]]


def clear_session():
    return '', None


def predict(input,
            large_language_model,
            embedding_model,
            top_k,
            use_web,
            use_pattern,
            history=None):
    # print(large_language_model, embedding_model)
    print(input)
    if history == None:
        history = []

    if use_web == '使用':
        web_content = application.source_service.search_web(query=input)
    else:
        web_content = ''
    search_text = ''
    if use_pattern == '模型问答':
        result = application.get_llm_answer(query=input, web_content=web_content)
        history.append((input, result))
        search_text += web_content
        return '', history, history, search_text

    else:
        response, _,contents = application.chat(
            question=input,
            topk=top_k,
        )
        history.append((input, response))
        for idx, source in enumerate(contents[:5]):
            sep = f'----------【搜索结果{idx + 1}：】---------------\n'
            search_text += f'{sep}\n{source}\n\n'
        print(search_text)
        search_text += "----------【网络检索内容】-----------\n"
        search_text += web_content
        return '', history, history, search_text


with gr.Blocks(theme="soft") as demo:
    gr.Markdown("""<h1><center>Gomate Application</center></h1>
        <center><font size=3>
        </center></font>
        """)
    state = gr.State()

    with gr.Row():
        with gr.Column(scale=1):
            embedding_model = gr.Dropdown([
                "text2vec-base",
                "bge-large-v1.5",
                "bge-base-v1.5",
            ],
                label="Embedding model",
                value="bge-large-v1.5")

            large_language_model = gr.Dropdown(
                [
                    "ChatGLM-6B-int4",
                ],
                label="large language model",
                value="ChatGLM-6B-int4")

            top_k = gr.Slider(1,
                              20,
                              value=4,
                              step=1,
                              label="检索top-k文档",
                              interactive=True)

            use_web = gr.Radio(["使用", "不使用"], label="web search",
                               info="是否使用网络搜索，使用时确保网络通常",
                               value="不使用", interactive=False
                               )
            use_pattern = gr.Radio(
                [
                    '模型问答',
                    '知识库问答',
                ],
                label="模式",
                value='知识库问答',
                interactive=False)

            kg_name = gr.Radio(["伊朗新闻"],
                               label="知识库",
                               value=None,
                               info="使用知识库问答，请加载知识库",
                               interactive=True)
            set_kg_btn = gr.Button("加载知识库")

            file = gr.File(label="将文件上传到知识库库，内容要尽量匹配",
                           visible=True,
                           file_types=['.txt', '.md', '.docx', '.pdf']
                           )

        with gr.Column(scale=4):
            with gr.Row():
                chatbot = gr.Chatbot(label='Gomate Application').style(height=400)
            with gr.Row():
                message = gr.Textbox(label='请输入问题')
            with gr.Row():
                clear_history = gr.Button("🧹 清除历史对话")
                send = gr.Button("🚀 发送")
            with gr.Row():
                gr.Markdown("""提醒：<br>
                                        [Gomate Application](https://github.com/gomate-community/GoMate) <br>
                                        有任何使用问题[Github Issue区](https://github.com/gomate-community/GoMate)进行反馈. 
                                        <br>
                                        """)
        with gr.Column(scale=2):
            search = gr.Textbox(label='搜索结果')

        # ============= 触发动作=============
        file.upload(upload_file,
                    inputs=file,
                    outputs=None)
        set_kg_btn.click(
            set_knowledge,
            show_progress=True,
            inputs=[kg_name, chatbot],
            outputs=chatbot
        )
        # 发送按钮 提交
        send.click(predict,
                   inputs=[
                       message,
                       large_language_model,
                       embedding_model,
                       top_k,
                       use_web,
                       use_pattern,
                       state
                   ],
                   outputs=[message, chatbot, state, search])

        # 清空历史对话按钮 提交
        clear_history.click(fn=clear_session,
                            inputs=[],
                            outputs=[chatbot, state],
                            queue=False)

        # 输入框 回车
        message.submit(predict,
                       inputs=[
                           message,
                           large_language_model,
                           embedding_model,
                           top_k,
                           use_web,
                           use_pattern,
                           state
                       ],
                       outputs=[message, chatbot, state, search])

demo.queue(concurrency_count=2).launch(
    server_name='0.0.0.0',
    server_port=7860,
    share=True,
    show_error=True,
    debug=True,
    enable_queue=True,
    inbrowser=False,
)
