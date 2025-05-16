from typing import Dict, List, Any, Optional, Tuple
import logging
import numpy as np
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os

class IntentClassifier:
    """
    Classifies user intent from text input.
    Supports different model backends for classification.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the intent classifier with configuration.
        
        Args:
            config: Dictionary containing classifier configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.model_type = config.get("model_type", "llm")  # llm, sklearn, custom
        self.model_path = config.get("model_path")
        self.labels = config.get("labels", [])
        self.threshold = config.get("threshold", 0.5)
        self.llm_client = None
        self.model = None
        self.vectorizer = None
        
        # Load model if specified and exists
        if self.model_type in ["sklearn", "custom"] and self.model_path:
            self._load_model()
        
        # Set up LLM client if using LLM-based classification
        if self.model_type == "llm" and "llm_client" in config:
            self.llm_client = config["llm_client"]
        
        self.logger.info(f"Initialized Intent Classifier with type: {self.model_type}")
    
    def _load_model(self):
        """Load model and vectorizer from disk if available"""
        try:
            if os.path.exists(self.model_path):
                model_data = joblib.load(self.model_path)
                self.model = model_data.get("model")
                self.vectorizer = model_data.get("vectorizer")
                self.labels = model_data.get("labels", self.labels)
                self.logger.info(f"Loaded intent classifier model from {self.model_path}")
            else:
                self.logger.warning(f"Model path {self.model_path} does not exist")
        except Exception as e:
            self.logger.error(f"Error loading model: {str(e)}")
    
    def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify the intent of the input text.
        
        Args:
            text: Input text to classify
            
        Returns:
            Dictionary containing intent classification results
        """
        if not text:
            return {"intent": None, "confidence": 0.0, "all_intents": {}}
        
        self.logger.debug(f"Classifying intent for text: {text[:50]}...")
        
        if self.model_type == "llm":
            return self._classify_with_llm(text)
        elif self.model_type in ["sklearn", "custom"]:
            return self._classify_with_model(text)
        else:
            self.logger.error(f"Unsupported model type: {self.model_type}")
            return {"intent": None, "confidence": 0.0, "all_intents": {}}
    
    def _classify_with_llm(self, text: str) -> Dict[str, Any]:
        """Classify intent using an LLM"""
        if not self.llm_client:
            self.logger.error("LLM client not configured for intent classification")
            return {"intent": None, "confidence": 0.0, "all_intents": {}}
        
        try:
            # Prepare prompt with available intents
            intent_list = "\n".join([f"- {label}" for label in self.labels])
            prompt = (
                f"Classify the following text into one of these intents:\n"
                f"{intent_list}\n\n"
                f"Text: \"{text}\"\n\n"
                f"Respond with the intent name and a confidence score between 0 and 1. "
                f"Format: {{\"intent\": \"INTENT_NAME\", \"confidence\": SCORE}}"
            )
            
            # Get classification from LLM
            response = self.llm_client.generate(prompt)
            
            # Parse response - this assumes the LLM outputs valid JSON
            # In production, add more robust parsing logic
            import json
            try:
                result_text = response.get("text", "{}")
                # Extract JSON part if LLM added additional text
                if "{" in result_text and "}" in result_text:
                    json_start = result_text.find("{")
                    json_end = result_text.rfind("}") + 1
                    json_str = result_text[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    result = json.loads(result_text)
                
                intent = result.get("intent")
                confidence = float(result.get("confidence", 0.0))
                
                # Check if the predicted intent is in our known labels
                if intent not in self.labels:
                    self.logger.warning(f"LLM predicted unknown intent: {intent}")
                    # Fall back to most relevant known intent
                    if self.labels:
                        intent = self.labels[0]
                    else:
                        intent = None
                
                all_intents = {intent: confidence} if intent else {}
                
                return {
                    "intent": intent,
                    "confidence": confidence,
                    "all_intents": all_intents,
                    "method": "llm"
                }
                
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse LLM response: {response.get('text')}")
                return {"intent": None, "confidence": 0.0, "all_intents": {}, "method": "llm"}
                
        except Exception as e:
            self.logger.error(f"Error in LLM intent classification: {str(e)}")
            return {"intent": None, "confidence": 0.0, "all_intents": {}, "method": "llm"}
    
    def _classify_with_model(self, text: str) -> Dict[str, Any]:
        """Classify intent using sklearn or custom model"""
        if not self.model or not self.vectorizer:
            self.logger.error("Model or vectorizer not loaded for intent classification")
            return {"intent": None, "confidence": 0.0, "all_intents": {}}
        
        try:
            # Vectorize the text
            text_vectorized = self.vectorizer.transform([text])
            
            # Predict intent probabilities
            probabilities = self.model.predict_proba(text_vectorized)[0]
            
            # Create intent-probability mapping
            all_intents = {label: float(prob) for label, prob in zip(self.labels, probabilities)}
            
            # Get the highest probability intent
            sorted_intents = sorted(all_intents.items(), key=lambda x: x[1], reverse=True)
            top_intent, top_prob = sorted_intents[0]
            
            # Check confidence threshold
            intent = top_intent if top_prob >= self.threshold else None
            
            return {
                "intent": intent,
                "confidence": float(top_prob),
                "all_intents": all_intents,
                "method": "model"
            }
            
        except Exception as e:
            self.logger.error(f"Error in model intent classification: {str(e)}")
            return {"intent": None, "confidence": 0.0, "all_intents": {}, "method": "model"}
    
    def get_top_intents(self, text: str, n: int = 3) -> List[Dict[str, Any]]:
        """
        Get the top N intent classifications.
        
        Args:
            text: Input text to classify
            n: Number of top intents to return
            
        Returns:
            List of dictionaries containing intent name and confidence
        """
        classification = self.classify(text)
        all_intents = classification.get("all_intents", {})
        
        # Sort by confidence and take top N
        top_intents = sorted(all_intents.items(), key=lambda x: x[1], reverse=True)[:n]
        
        return [{"intent": intent, "confidence": conf} for intent, conf in top_intents]
    
    def train(self, texts: List[str], labels: List[str], **kwargs) -> Dict[str, Any]:
        """
        Train or fine-tune the intent model.
        
        Args:
            texts: List of training text samples
            labels: List of corresponding intent labels
            **kwargs: Additional training parameters
            
        Returns:
            Dictionary containing training results
        """
        if self.model_type == "llm":
            self.logger.warning("Training not supported for LLM-based classification")
            return {"success": False, "error": "Training not supported for LLM"}
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            
            # Validate inputs
            if len(texts) != len(labels):
                raise ValueError("Texts and labels must have the same length")
            
            if len(texts) < 10:
                raise ValueError("Insufficient training data (minimum 10 examples needed)")
            
            # Gather unique labels
            unique_labels = sorted(set(labels))
            
            # Split data
            test_size = kwargs.get("test_size", 0.2)
            X_train, X_test, y_train, y_test = train_test_split(
                texts, labels, test_size=test_size, random_state=42, stratify=labels
            )
            
            # Create vectorizer
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=10000,
                min_df=2
            )
            X_train_vectorized = self.vectorizer.fit_transform(X_train)
            
            # Create and train model
            self.model = RandomForestClassifier(
                n_estimators=kwargs.get("n_estimators", 100),
                max_depth=kwargs.get("max_depth", 10),
                random_state=42
            )
            self.model.fit(X_train_vectorized, y_train)
            
            # Evaluate on test set
            X_test_vectorized = self.vectorizer.transform(X_test)
            y_pred = self.model.predict(X_test_vectorized)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Save model if path is specified
            if self.model_path:
                model_data = {
                    "model": self.model,
                    "vectorizer": self.vectorizer,
                    "labels": unique_labels
                }
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                joblib.dump(model_data, self.model_path)
                self.logger.info(f"Saved intent classifier model to {self.model_path}")
            
            # Update instance variables
            self.labels = unique_labels
            
            return {
                "success": True,
                "accuracy": float(accuracy),
                "num_samples": len(texts),
                "num_classes": len(unique_labels),
                "model_path": self.model_path
            }
            
        except Exception as e:
            self.logger.error(f"Error training intent classifier: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def evaluate(self, texts: List[str], labels: List[str]) -> Dict[str, Any]:
        """
        Evaluate model performance on a test dataset.
        
        Args:
            texts: List of test text samples
            labels: List of corresponding intent labels
            
        Returns:
            Dictionary containing evaluation metrics
        """
        if not self.model or not self.vectorizer:
            return {"success": False, "error": "Model not initialized"}
        
        try:
            # Vectorize test data
            X_test_vectorized = self.vectorizer.transform(texts)
            
            # Get predictions
            y_pred = self.model.predict(X_test_vectorized)
            
            # Calculate metrics
            accuracy = accuracy_score(labels, y_pred)
            report = classification_report(labels, y_pred, output_dict=True)
            
            # Extract metrics by class
            class_metrics = {}
            for label in set(labels):
                if label in report:
                    class_metrics[label] = {
                        "precision": report[label]["precision"],
                        "recall": report[label]["recall"],
                        "f1-score": report[label]["f1-score"],
                        "support": report[label]["support"]
                    }
            
            return {
                "success": True,
                "accuracy": float(accuracy),
                "class_metrics": class_metrics,
                "num_samples": len(texts),
                "macro_avg": report["macro avg"],
                "weighted_avg": report["weighted avg"]
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluating intent classifier: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        }