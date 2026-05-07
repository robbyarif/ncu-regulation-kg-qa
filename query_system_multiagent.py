from __future__ import annotations
import os
from typing import Any
from dotenv import load_dotenv
from agents.multi_agent_system import build_system_pipeline

# Ensure environment variables are loaded
load_dotenv()

# Initialize the pipeline
PIPELINE = None

def get_pipeline():
    global PIPELINE
    if PIPELINE is None:
        PIPELINE = build_system_pipeline()
    return PIPELINE

def answer_question(question: str) -> dict[str, Any]:
    """
    Main entry point for the multi-agent QA system.
    """
    pipe = get_pipeline()
    
    nlu = pipe["nlu"]
    security_agent = pipe["security"]
    planner = pipe["planner"]
    executor = pipe["executor"]
    diagnosis_agent = pipe["diagnosis"]
    repair_agent = pipe["repair"]
    responder = pipe["responder"]
    explanation_agent = pipe["explanation"]

    # 1. NLU
    intent = nlu.run(question)
    
    # 2. Security
    security = security_agent.run(question, intent)
    if security["decision"] == "REJECT":
        diagnosis = {"label": "QUERY_ERROR", "reason": "Blocked by security policy."}
        answer = f"I'm sorry, but I cannot fulfill this request. {security['reason']}"
        explanation = explanation_agent.run(question, intent, security, diagnosis, answer, False)
        return {
            "answer": answer,
            "safety_decision": "REJECT",
            "diagnosis": "QUERY_ERROR",
            "repair_attempted": False,
            "repair_changed": False,
            "explanation": explanation,
        }

    # 3. Planning
    plan = planner.run(intent)
    
    # 4. Execution
    execution = executor.run(plan)
    
    # 5. Diagnosis
    diagnosis = diagnosis_agent.run(execution, intent)

    repair_attempted = False
    repair_changed = False
    
    # 6. Repair if needed
    if diagnosis["label"] in {"QUERY_ERROR", "NO_DATA"}:
        repair_attempted = True
        repaired_plan = repair_agent.run(diagnosis, plan, intent)
        
        # Check if plan actually changed
        if repaired_plan["params"]["search_text"] != plan["params"]["search_text"]:
            repair_changed = True
            execution = executor.run(repaired_plan)
            diagnosis = diagnosis_agent.run(execution, intent)

    # 7. Response Generation
    if diagnosis["label"] == "SUCCESS":
        answer = responder.run(question, execution["rows"])
    elif diagnosis["label"] == "NO_DATA":
        answer = "I'm sorry, I couldn't find any specific regulations related to your question in the knowledge graph."
    else:
        answer = f"An error occurred while processing your query: {diagnosis['reason']}"

    # 8. Explanation
    explanation = explanation_agent.run(question, intent, security, diagnosis, answer, repair_attempted)
    
    return {
        "answer": answer,
        "safety_decision": "ALLOW",
        "diagnosis": diagnosis["label"],
        "repair_attempted": repair_attempted,
        "repair_changed": repair_changed,
        "explanation": explanation,
    }

def run_multiagent_qa(question: str) -> dict[str, Any]:
    return answer_question(question)

def run_qa(question: str) -> dict[str, Any]:
    return answer_question(question)

if __name__ == "__main__":
    print("🎓 NCU Regulation Multi-Agent Assistant")
    while True:
        q = input("\nQuestion (type exit): ").strip()
        if not q or q.lower() in {"exit", "quit"}:
            break
        result = answer_question(q)
        print(f"\nResponse: {result['answer']}")
        print(f"Safety: {result['safety_decision']}")
        print(f"Diagnosis: {result['diagnosis']}")
        print(f"Repair: {result['repair_attempted']} (Changed: {result['repair_changed']})")
        print("-" * 30)
