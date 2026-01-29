def build_prompt(context, question):
    return f"""=
Answer ONLY using the context below.
If the answer is not explicitly stated, say "I don't know".
If the question contains an unsupported assumption, say
"The document does not support that statement."
Do NOT use prior knowledge.


Context:
{context}

Question:
{question}
"""
