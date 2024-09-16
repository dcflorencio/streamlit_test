import autogen
import os
from dotenv import load_dotenv
from autogen import AssistantAgent, UserProxyAgent
from autogen import ConversableAgent, UserProxyAgent, config_list_from_json
from autogen import register_function
# import sqlite3
import http.client
from typing import Any, Dict
from pathlib import Path
from typing import List, Any
import agentops
import streamlit as st
import asyncio

# Load environment variables from .env file
load_dotenv()

# Get the API key from the environment variable
api_key = os.getenv("OPENAI_API_KEY")
api_key_ops = os.getenv("AGENTOPS_API_KEY")
rapidapi_key = os.getenv("RAPIDAPI_KEY")

agentops.init(api_key=api_key_ops)


# # Lesson 6: Planning and Stock Report Generation

# ## Setup

config_list = [
    {
        'model': 'gpt-4o-mini',
        'api_key': api_key
    }
]

# ## Setup

llm_config={

    "seed": 42,
    "config_list": config_list,
    "temperature": 0
}

# DEFINE TOOLS

def fetch_zillow_data(location: str = None, page: int = 1, status_type: str = None, home_type: str = None, sort: str = None,
                      min_price: int = None, max_price: int = None, rent_min_price: int = None, rent_max_price: int = None,
                      baths_min: int = None, baths_max: int = None, beds_min: int = None, beds_max: int = None,
                      sqft_min: int = None, sqft_max: int = None, days_on: int = None, sold_in_last: int = None,
                      keywords: str = None) -> Dict[str, Any]:
    """
    Function to query Zillow API for real estate listings based on provided parameters.
    All parameters are optional.

    :param location: Location to search (e.g., 'San Francisco').
    :param page: Page number of the result set (default is 1).
    :param status_type: Property status ('ForSale', 'ForRent').
    :param home_type: Type of home (e.g., if status_type = ForSale then 'Apartments', 'Houses', 'Condos', 'Townhomes' ; if status_type = ForRent then 'Houses', 'Townhomes', 'Apartments_Condos_Co-ops'; ).
    :param sort: Sorting option (e.g., if status_type = ForSale then 'Price_Low_High'; if status_type = ForRent then 'Payment_Low_High').
    :param min_price: Minimum price.
    :param max_price: Maximum price.
    :param rent_min_price: Minimum rent price.
    :param rent_max_price: Maximum rent price.
    :param baths_min: Minimum number of bathrooms.
    :param baths_max: Maximum number of bathrooms.
    :param beds_min: Minimum number of bedrooms.
    :param beds_max: Maximum number of bedrooms.
    :param sqft_min: Minimum square footage.
    :param sqft_max: Maximum square footage.
    :param days_on: Number of days on the market.
    :param sold_in_last: Filter for sold in the last 'x' days.
    :param keywords: Keywords for search (e.g., 'modern house 2 stories').
    
    :return: A dictionary containing the Zillow API response.
    """
    
    # Create a connection to the Zillow API via HTTPS
    conn = http.client.HTTPSConnection("zillow-com1.p.rapidapi.com")

    # Set the required API headers with your API key and host information
    headers = {
        'x-rapidapi-key': rapidapi_key,
        'x-rapidapi-host': "zillow-com1.p.rapidapi.com"
    }

    # Prepare query parameters, only include if not None
    query_params = []
    if location:
        query_params.append(f"location={location.replace(' ', '%20')}")
    query_params.append(f"page={page}")
    if status_type:
        query_params.append(f"status_type={status_type}")
    if home_type:
        query_params.append(f"home_type={home_type}")
    if sort:
        query_params.append(f"sort={sort}")
    if min_price is not None:
        query_params.append(f"minPrice={min_price}")
    if max_price is not None:
        query_params.append(f"maxPrice={max_price}")
    if rent_min_price is not None:
        query_params.append(f"rentMinPrice={rent_min_price}")
    if rent_max_price is not None:
        query_params.append(f"rentMaxPrice={rent_max_price}")
    if baths_min is not None:
        query_params.append(f"bathsMin={baths_min}")
    if baths_max is not None:
        query_params.append(f"bathsMax={baths_max}")
    if beds_min is not None:
        query_params.append(f"bedsMin={beds_min}")
    if beds_max is not None:
        query_params.append(f"bedsMax={beds_max}")
    if sqft_min is not None:
        query_params.append(f"sqftMin={sqft_min}")
    if sqft_max is not None:
        query_params.append(f"sqftMax={sqft_max}")
    if days_on is not None:
        query_params.append(f"daysOn={days_on}")
    if sold_in_last is not None:
        query_params.append(f"soldInLast={sold_in_last}")
    if keywords:
        query_params.append(f"keywords={keywords.replace(' ', '%20')}")

    # Join the query parameters with & to form the final query string
    query_string = "?" + "&".join(query_params)

    # Send the GET request with the headers and query parameters
    conn.request("GET", f"/propertyExtendedSearch{query_string}", headers=headers)

    # Get the response from the API
    response = conn.getresponse()
    data = response.read()

    # Decode and return the response data as a dictionary
    return {
        "status": response.status,
        "reason": response.reason,
        "data": data.decode("utf-8")
    }



# SAVE MARKDOWN FILE
def save_markdown_file(filename: str, content: str) -> None:
    """
    Function to save a Markdown file to the current folder.

    :param filename: The name of the Markdown file (should include .md extension).
    :param content: The content to be written to the Markdown file.
    :return: None.
    """
    
    # Ensure the filename ends with .md extension
    if not filename.endswith(".md"):
        filename += ".md"
    
    try:
        # Write content to the Markdown file
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
        
        # Log the successful save
        print(f"Markdown file saved successfully: {filename}")
        
    except IOError as e:
        # Handle errors in writing to the file
        print(f"An error occurred while saving the Markdown file: {e}")

# Example usage:
# save_markdown_file("example_markdown", "# This is a title\n\nThis is some content in Markdown.")


# ## The task!

task = """Generate a real estate report to show some homes I am interested"""

# ## Build a group chat
# 
# This group chat will include these agents:
# 
# 1. **User_proxy** or **Admin**: to allow the user to comment on the report and ask the writer to refine it.
# 2. **Planner**: to determine relevant information needed to complete the task.
# 3. **Engineer**: to write code using the defined plan by the planner.
# 4. **Executor**: to execute the code written by the engineer.
# 5. **Writer**: to write the report.

########## STREAMLIT ##############
st.write("""# REAL ESTATE FINDER""")


class TrackableUSER(ConversableAgent):
    def _process_received_message(self, message, sender, silent):
        content = message.get('content', message) if isinstance(message, dict) else message

        with st.chat_message(sender.name):
            st.markdown(content)
        return super()._process_received_message(message, sender, silent)


class TrackablePLANNER(ConversableAgent):
    def _process_received_message(self, message, sender, silent):
        content = message.get('content', message) if isinstance(message, dict) else message
        with st.chat_message(sender.name):
            st.markdown(content)
        return super()._process_received_message(message, sender, silent)

class TrackableWRITER(ConversableAgent):
    def _process_received_message(self, message, sender, silent):
        content = message.get('content', message) if isinstance(message, dict) else message
        with st.chat_message(sender.name):
            st.markdown(content)
        return super()._process_received_message(message, sender, silent)

user_input = st.chat_input(task)

with st.container():


    if user_input:
        
        user_proxy = TrackableUSER(
            name="Admin",
            system_message="Give the task, and send "
            "instructions to writer to refine the real estate report.",
            code_execution_config=False,
            llm_config=llm_config,
            human_input_mode="ALWAYS",
        )

        planner = TrackablePLANNER(
            name="Planner",
            system_message="Given a task, please determine "
            "what information is needed to complete the task. "
            "Please note that the information will all be retrieved using"
            " Python code. Please only suggest information that can be "
            "retrieved using Python code. "
            "Dont suggest the actual code, pass the suggested parameters to the engineer and they will take care of the code."
            "After each step is done by others, check the progress and "
            "instruct the remaining steps. If a step fails, try to "
            "workaround",
            description="Planner. Given a task, determine what "
            "information is needed to complete the task. "
            "After each step is done by others, check the progress and "
            "instruct the remaining steps",
            llm_config=llm_config,
        )

        engineer = autogen.AssistantAgent(
            name="Engineer",
            llm_config=llm_config,
            description="An engineer that writes code based on the plan "
            "provided by the planner. ",
            system_message="""You are a helpful AI assistant.
        Solve tasks using your coding and language skills.
        In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
            1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
            2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
        Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
        When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
        If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
        If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
        When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
        You may need to call the function fetch_zillow_data() to query Zillow API data. Use the `fetch_zillow_data` function to fetch real estate listings based on various parameters such as location, price, and home type.
        If you need to fetch zillow data call the function, do not generate new code call the fetch_zillow_data() function.
        The `fetch_zillow_data` function accepts the following parameters, use only the necessary ones:
        - `location`: The location for the search (e.g., 'San Francisco'). Ensure that spaces are URL-encoded as `%20`.
        - `page`: The page number for the result set (e.g., 1).
        - `status_type`: The property status ('ForSale', 'ForRent').
        - `home_type`: The type of home (e.g., if status_type = ForSale then 'Apartments', 'Houses', 'Condos', 'Townhomes' ; if status_type = ForRent then 'Houses', 'Townhomes', 'Apartments_Condos_Co-ops'; ).
        - `sort`: The sorting order if status_type = ForSale then 'Price_Low_High'; if status_type = ForRent then 'Payment_Low_High').
        - `min_price`: The minimum price for the listing.
        - `max_price`: The maximum price for the listing.
        - `rent_min_price`: The minimum rent price for the listing.
        - `rent_max_price`: The maximum rent price for the listing.
        - `baths_min`: The minimum number of bathrooms.
        - `baths_max`: The maximum number of bathrooms.
        - `beds_min`: The minimum number of bedrooms.
        - `beds_max`: The maximum number of bedrooms.
        - `sqft_min`: The minimum square footage of the listing.
        - `sqft_max`: The maximum square footage of the listing.
        - `days_on`: The number of days the listing has been on the market.
        - `sold_in_last`: The time frame for sold listings (e.g., 'sold in the last 7 days').
        - `keywords`: Search keywords (e.g., 'modern house 2 stories'). Ensure that spaces in keywords are URL-encoded as `%20`.

        Always ensure that any spaces or special characters in parameters like `location` or `keywords` are properly URL-encoded before making the API call. Call this function with the necessary parameters to retrieve the relevant data. Always ensure the data you return is based on the actual function results, and never generate fictitious data.

        If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.

        Reply "TERMINATE" in the end when everything is done.
            """
        )

        # **Note**: In this lesson, you'll use an alternative method of code execution by providing a dict config. However, you can always use the LocalCommandLineCodeExecutor if you prefer. For more details about code_execution_config, check this: https://microsoft.github.io/autogen/docs/reference/agentchat/conversable_agent/#__init__

        executor = autogen.ConversableAgent(
            name="Executor",
            system_message="Execute the code written by the "
            "engineer and report the result.",
            human_input_mode="NEVER",
            code_execution_config={
                "last_n_messages": 3,
                "work_dir": "coding",
                "use_docker": False,
            },
        )

        writer = TrackableWRITER(
            name="Writer",
            llm_config=llm_config,
            system_message="""Writer.
            Please write a real estate report.
            Include a photo for each listing.
            You take feedback from the user/admin and refine your report.
            Every time you generate a report, ALWAYS save it as a markdown file calling the save_markdown_file() function.
            Always ask the user/admin for feedback.
            If the user asks for different data DON'T MAKE UP DATA, ALWAYS ask the engineer to query the new data the user asked.
            NEVER MAKE UP FICTITIOUS DATA.
            dont forget to CALL THE save_markdown_file()""",

            description="""Writer.
            Write real estate report based on the code execution results and take 
            feedback from the admin to refine the report."""
        )



        ## REGISTER THE TOOLS



        # fetch_zillow_data
        register_function(
            fetch_zillow_data,
            caller=engineer,  # The assistant agent can suggest calls to the calculator.
            executor=executor,  # The user proxy agent can execute the calculator calls.
            name="fetch_zillow_data",  # By default, the function name is used as the tool name.
            description="A tool that fetches zillow data",  # A description of the tool.
        )

        # save_markdown_file
        register_function(
            save_markdown_file,
            caller=writer,  # The assistant agent can suggest calls to the calculator.
            executor=executor,  # The user proxy agent can execute the calculator calls.
            name="save_markdown_file",  # By default, the function name is used as the tool name.
            description="A tool that saves a markdown file to the current folder",  # A description of the tool.
        )


        
        # ## Define the group chat

        groupchat = autogen.GroupChat(
            agents=[user_proxy, engineer, writer, executor, planner],
            messages=[],
            max_round=20,
        )

        manager = autogen.GroupChatManager(
            groupchat=groupchat, llm_config=llm_config
        )


        # ## Start the group chat!

        # <p style="background-color:#ECECEC; padding:15px; "> <b>Note:</b> In this lesson, you will use GPT 4 for better results. Please note that the lesson has a quota limit. If you want to explore the code in this lesson further, we recommend trying it locally with your own API key.

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        print('loop before')

        async def initiate_chat():
            await user_proxy.initiate_chat(
                manager,
                message=task,
            )
        
        loop.run_until_complete(initiate_chat())
        
        print('loop after')

print('loop outside')

agentops.end_session("Success")