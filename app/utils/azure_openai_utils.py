from openai import AzureOpenAI

"""
This module provides utility functions for interacting with Azure OpenAI models.
"""
import json


def _call_model(
    client: AzureOpenAI,
    model_deployment,
    messages,
    response_format=None,
    max_tokens=3200,
    temperature=None,
    top_p=None,
):

    completion = client.chat.completions.create(
        model=model_deployment,
        messages=messages,
        response_format=response_format,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
    )
    return json.loads(completion.choices[0].message.content)

def call_model(
    client: AzureOpenAI,
    model_deployment,
    system_prompt,
    user_prompt,
    response_format=None,
):
    """
    Calls the Azure OpenAI model with the given prompts and a specified response format.

    Args:
        client (AzureOpenAI): The Azure OpenAI client instance.
        model_deployment (str): The model deployment identifier.
        system_prompt (str): The system prompt to set the context for the model.
        user_prompt (str): The user prompt to be processed by the model.
        response_format (dict): The format in which the response should be returned.

    Returns:
        dict: The response from the model.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    return _call_model(client, model_deployment, messages, response_format)


def call_model_batch(
    client: AzureOpenAI, model_deployment, system_prompt, user_prompts, response_format
):
    """
    Calls the Azure OpenAI model with a batch of user prompts.
    NOTE: Not sure if this is the best way to do this, so will be evaluating its performance,
    will likely handle batching outside of the llm.

    Args:
        client (AzureOpenAI): The Azure OpenAI client instance.
        model_deployment (str): The model deployment identifier.
        system_prompt (str): The system prompt to set the context for the model.
        user_prompts (list): A list of user prompts to be processed by the model.
        response_format (dict): The format in which the response should be returned.

    Returns:
        list: A list of responses from the model for each user prompt.
    """
    messages = [{"role": "system", "content": system_prompt}] + [
        {"role": "user", "content": user_prompt} for user_prompt in user_prompts
    ]
    return _call_model(client, model_deployment, messages, response_format)["responses"]
