import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

logger = logging.getLogger("uvicorn.error")

# Mock dataset to train the inline routing heuristic model on module evaluation
TRAINING_PROMPTS = [
    # Tier 0: Simple, short conversational phrases
    ("hi", 0), ("hello", 0), ("hey there", 0), ("test", 0), ("ok", 0),
    
    # Tier 1: Medium complexity data manipulation or text formatting tasks
    ("clean up this data format and remove spaces", 1),
    ("convert this list of names into a standard comma separated string", 1),
    ("extract all email addresses from this unformatted text log block", 1),
    
    # Tier 2: Heavy engineering, structural analysis, code optimization, or JSON generations
    ("Analyze the log stream structure, evaluate if the routing tiers are optimal, and compare configurations in JSON format", 2),
    ("Write a complete high availability network failover script in python using asynchronous connections", 2),
    ("Optimize this raw SQL query execution plan to prevent table scans and add indexed constraints", 2)
]

def _train_routing_pipeline() -> Pipeline:
    """
    Constructs, fits, and evaluates an inline text classification model pipeline.
    """
    try:
        X = [text for text, _ in TRAINING_PROMPTS]
        y = [label for _, label in TRAINING_PROMPTS]
        
        # Initialize a standard TF-IDF and Logistic Regression classification model sequence
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(lowercase=True, stop_words='english', ngram_range=(1, 2))),
            ('clf', LogisticRegression(C=1.0, max_iter=200))
        ])
        
        pipeline.fit(X, y)
        return pipeline
    except Exception as e:
        logger.critical(f"💥 Failed to initialize ML Classifier Pipeline: {str(e)}")
        raise e

# Instantiate the singleton model architecture pipeline globally on execution
_CLASSIFIER_PIPELINE = _train_routing_pipeline()

def predict_complexity_tier(prompt: str) -> int:
    """
    Evaluates an incoming prompt string against the vectorizer matrix to return an absolute 
    predicted operational complexity threshold tier (0, 1, or 2).
    """
    if not prompt or not prompt.strip():
        return 0
        
    try:
        prediction = _CLASSIFIER_PIPELINE.predict([prompt])[0]
        tier = int(prediction)
        logger.info(f"🔮 ML Classifier classified workload prompt footprint to Complexity Tier: {tier}")
        return tier
    except Exception as e:
        logger.error(f"Fallback warning: Classification engine encountered an error: {str(e)}. Defaulting to Tier 0.")
        return 0

def bootstrap_classifier():
    """
    Ecosystem initialization hook invoked by the application lifespan context manager.
    Forces the Python interpreter to evaluate the module space and pre-warm the Scikit-Learn
    vectorizer pipelines into host memory layout lines on startup.
    """
    logger.info("🎯 Scikit-Learn operational classification pipelines successfully pre-warmed.")