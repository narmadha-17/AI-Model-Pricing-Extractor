# -*- coding: utf-8 -*-
"""model_Cost_cal_gradio.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/10QbLbTBEarxLwaIBD4NCkC0kGOi1LANR
"""

!pip install tavily-python
!pip install langchain_openai

import gradio as gr
import pandas as pd
from pydantic import BaseModel, Field
from typing import List
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from tavily import TavilyClient

try:
    from google.colab import userdata
except ImportError:
    class userdata:
        @staticmethod
        def get(key):
            return None

class ModelPricing(BaseModel):
    model_name: str = Field(..., description="Name of the model")
    cost_per_1M_input_token: float = Field(..., description="Cost per 1M tokens in USD")
    cost_per_1M_output_token: float = Field(..., description="Cost per 1M tokens in USD")

class PricingList(BaseModel):
    pricinglist: List[ModelPricing]

import os

try:
    TAVILY_API_KEY = "secret"
    OPENAI_API_KEY = "secret"
    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
except Exception as e:
    print("API key setup needed. Please set your keys ")
    llm, tavily_client = None, None

def extract_pricing_from_url(url: str, model_names: List[str], provider: str) -> pd.DataFrame:
    if not llm or not tavily_client:
        return pd.DataFrame({"Error": ["API keys not configured. Please check setup instructions above."]})

    try:
        page_content = tavily_client.crawl(url)['results']

        model_list_str = "\n- " + "\n- ".join(model_names)
        prompt = PromptTemplate(
            template=f"""
You are an extraction engine.

From the following documentation content, extract pricing details ONLY for the following {provider} models:
{model_list_str}

For each model, extract:
- model_name
- cost_per_1M_input_token(USD)
- cost_per_1M_output_token(USD)

Documentation:
\"\"\"
{{doc}}
\"\"\"
""",
            input_variables=["doc"],
        )

        chain = prompt | llm.with_structured_output(PricingList)
        output = chain.invoke({"doc": page_content})

        df = pd.DataFrame([m.dict() for m in output.pricinglist])
        df["provider"] = provider
        return df

    except Exception as e:
        return pd.DataFrame({"Error": [f"Failed to extract pricing: {str(e)}"]})

def get_predefined_pricing():
    """Get pricing for predefined models"""
    if not llm or not tavily_client:
        return pd.DataFrame({"Error": [" API keys not configured. Please set up your keys first."]})

    try:
        openai_url = "https://openai.com/api/pricing/"
        openai_models = ["GPT-4o", "GPT-4o mini", "GPT-4.1", "GPT-4.1 mini", "GPT-4.1 nano"]
        openai_df = extract_pricing_from_url(openai_url, openai_models, "OpenAI")

        gemini_url = "https://ai.google.dev/gemini-api/docs/pricing"
        gemini_models = ["Gemini 2.0 Flash", "Gemini 2.0 Flash-lite"]
        gemini_df = extract_pricing_from_url(gemini_url, gemini_models, "Gemini")

        if "Error" in openai_df.columns or "Error" in gemini_df.columns:
            return pd.DataFrame({"Error": ["Failed to extract pricing data. Check your API keys and internet connection."]})

        merged_df = pd.concat([openai_df, gemini_df], ignore_index=True)

        if merged_df.empty:
            return pd.DataFrame({"Error": ["No pricing data found. Please check your API keys and internet connection."]})

        return merged_df

    except Exception as e:
        return pd.DataFrame({"Error": [f"Error: {str(e)}"]})

def extract_custom_pricing(url: str, models_text: str, provider: str):
    """Extract pricing for custom URL and models"""
    if not llm or not tavily_client:
        return pd.DataFrame({"Error": [" API keys not configured. Please set up your keys first."]})

    if not url or not models_text or not provider:
        return pd.DataFrame({"Error": ["Please fill in all fields"]})

    try:
        model_names = [model.strip() for model in models_text.split('\n') if model.strip()]

        if not model_names:
            return pd.DataFrame({"Error": ["Please enter at least one model name"]})

        df = extract_pricing_from_url(url, model_names, provider)

        if "Error" in df.columns:
            return df

        if df.empty:
            return pd.DataFrame({"Error": [f"No pricing data found for {provider} models at {url}"]})

        return df

    except Exception as e:
        return pd.DataFrame({"Error": [f"Error: {str(e)}"]})

with gr.Blocks(title="AI Model Pricing Extractor", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# AI Model Pricing Extractor")
    gr.Markdown("Extract and compare pricing information from AI model providers")

    with gr.Tabs():
        with gr.TabItem("Quick Extract (OpenAI + Gemini)"):
            gr.Markdown("### Get latest pricing for popular models")

            get_pricing_btn = gr.Button(" Extract Pricing", variant="primary", size="lg")
            predefined_output = gr.Dataframe(
                headers=["Model Name", "Input Cost/1M", "Output Cost/1M", "Provider"],
                label="Pricing Results"
            )

            get_pricing_btn.click(
                fn=get_predefined_pricing,
                outputs=predefined_output
            )

        with gr.TabItem("Custom Extraction"):
            gr.Markdown("### Extract pricing from any provider")

            with gr.Row():
                with gr.Column():
                    custom_url = gr.Textbox(
                        label="Pricing URL",
                        placeholder="https://example.com/pricing",
                        info="URL of the pricing page to scrape"
                    )

                    custom_provider = gr.Textbox(
                        label="Provider Name",
                        placeholder="e.g., Anthropic, Cohere, etc.",
                        info="Name of the AI provider"
                    )

                    custom_models = gr.Textbox(
                        label="Model Names",
                        placeholder="Enter model names (one per line):\nClaude-3.5-Sonnet\nClaude-3-Haiku",
                        lines=5,
                        info="Enter each model name on a new line"
                    )

                with gr.Column():
                    extract_btn = gr.Button(" Extract Custom Pricing", variant="primary", size="lg")
                    custom_output = gr.Dataframe(
                        headers=["Model Name", "Input Cost/1M", "Output Cost/1M", "Provider"],
                        label="Custom Pricing Results"
                    )

            extract_btn.click(
                fn=extract_custom_pricing,
                inputs=[custom_url, custom_models, custom_provider],
                outputs=custom_output
            )

        with gr.TabItem("About"):
            gr.Markdown("""
            ### How it works:
            1. **Web Scraping**: Uses Tavily to crawl pricing pages
            2. **AI Extraction**: Uses GPT-4o-mini to extract structured pricing data
            3. **Results**: Displays pricing in an easy-to-compare table format

            ### Requirements:
            - OpenAI API key (for GPT-4o-mini)
            - Tavily API key (for web scraping)

            ### Setting up API Keys in Colab:
            1. **Using Colab Secrets (Recommended)**:
               - Click the  key icon in the left sidebar
               - Add `OPENAI_API_KEY` and `TAVILY_API_KEY`
               - Restart runtime after adding keys

            2. **Using Environment Variables**:
               ```python
               import os
               os.environ['OPENAI_API_KEY'] = 'your-openai-key'
               os.environ['TAVILY_API_KEY'] = 'your-tavily-key'
               ```

            ### Installation:
            ```bash
            !pip install gradio langchain-openai tavily-python pydantic pandas
            ```

            ### Supported Data:
            - Cost per 1M input tokens
            - Cost per 1M output tokens
            - Model names and providers
            """)

if __name__ == "__main__":
    demo.launch(
        share=True,
        debug=False,
        quiet=True,
        height=600,
        show_error=True
    )
    #https://mistral.ai/products/la-plateforme#pricing