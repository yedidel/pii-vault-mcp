# handle future agent continuation logic

def handle_claude(task: dict, event: dict):
    # later this will send a Claude Channel event
    print(f"Sending Claude continuation event for task {task['taskId']}")


def handle_openai(task: dict, event: dict):
    # later this will add a message to an OpenAI thread
    print(f"Sending OpenAI continuation event for task {task['taskId']}")


# map each platform to its continuation handler
CONTINUATION_HANDLERS = {
    "claude": handle_claude,
    "openai": handle_openai,
}


def resume_agent(task: dict, event: dict):
    # choose the correct handler by platform
    platform = task.get("platform")

    handler = CONTINUATION_HANDLERS.get(platform)

    if not handler:
        print(f"No continuation handler for platform: {platform}")
        return

    handler(task, event)