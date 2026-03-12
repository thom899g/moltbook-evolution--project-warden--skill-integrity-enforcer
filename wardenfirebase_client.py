"""
Firebase Firestore client for Project Warden
Handles all database operations with automatic retry and error handling
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from google.cloud.firestore import Client, DocumentReference, CollectionReference
from google.cloud.exceptions import GoogleCloudError

logger = logging.getLogger(__name__)

class FirebaseClient:
    """
    Firebase Firestore client with automatic initialization and error recovery
    Implements atomic operations with proper transaction handling
    """
    
    def __init__(self, config):
        """
        Initialize Firebase client with configuration
        
        Args:
            config: WardenConfig instance
        """
        self.config = config
        self._app = None
        self._db: Optional[Client] = None
        self._collections: Dict[str, CollectionReference] = {}
        
        self._initialize_firebase()
        self._initialize_collections()
        
        logger.info("FirebaseClient initialized successfully")
    
    def _initialize_firebase(self) -> None:
        """Initialize Firebase Admin SDK with error handling"""
        try:
            creds_path = Path(self.config.firebase_credentials_path)
            
            if not creds_path.exists():
                raise FileNotFoundError(f"Firebase credentials not found at {creds_path}")
            
            # Check if Firebase app already exists
            if not firebase_admin._apps:
                cred = credentials.Certificate(str(creds_path))
                self._app = initialize_app(cred, {
                    'projectId': self.config.firebase_project_id
                })
                logger.debug("Created new Firebase app instance")
            else:
                self._app = firebase_admin.get_app()
                logger.debug("Reused existing Firebase app instance")
            
            self._db = firestore.client(app=self._app)
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise RuntimeError(f"Firebase initialization failed: {e}")
    
    def _initialize_collections(self) -> None:
        """Initialize all Firestore collection references"""
        for name, collection_name in self.config.firestore_collections.items():
            self._collections[name] = self._db.collection(collection_name)
            logger.debug(f"Initialized collection: {name} -> {collection_name}")
    
    def get_collection(self, name: str) -> CollectionReference:
        """
        Get Firestore collection by name
        
        Args:
            name: Collection name from config
            
        Returns:
            CollectionReference
            
        Raises:
            ValueError: If collection name not found in config
        """
        if name not in self._collections:
            raise ValueError(f"Collection '{name}' not found in configuration")
        return self._collections[name]
    
    def create_document(self, collection_name: str, data: Dict[str, Any], 
                       document_id: Optional[str] = None) -> str:
        """
        Create a new document with automatic timestamp and error handling
        
        Args:
            collection_name: Name of collection
            data: Document data
            document_id: Optional document ID (auto-generated if None)
            
        Returns:
            Document ID of created document
            
        Raises:
            GoogleCloudError: If Firebase operation fails
        """
        try:
            collection = self.get_collection(collection_name)
            
            # Add metadata
            data['created_at'] = firestore.SERVER_TIMESTAMP
            data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            if document_id:
                doc_ref = collection.document(document_id)
                doc_ref.set(data)
                logger.debug(f"Created document {document_id} in {collection_name}")
            else:
                doc_ref = collection.add(data)[1]
                document_id = doc_ref.id
                logger.debug(f"Created auto-ID document {document_id} in {collection_name}")
            
            return document_id
            
        except GoogleCloudError as e:
            logger.error(f"Failed to create document in {collection_name}: {e}")
            raise
    
    def get_document(self, collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by ID with error handling
        
        Args:
            collection_name: Name of collection
            document_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        try:
            collection = self.get_collection(collection_name)
            doc_ref = collection.document(document_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            else:
                logger.debug(f"Document {document_id} not found in {collection_name}")
                return None
                
        except GoogleCloudError as e:
            logger.error(f"Failed to get document {document_id} from {collection_name}: {e}")
            return None
    
    def update_document(self, collection_name: str, document_id: str, 
                       data: Dict[str, Any], merge: bool = True) -> bool:
        """
        Update existing document
        
        Args:
            collection_name: Name of collection
            document_id: Document ID
            data: Data to update
            merge: Whether to merge with existing data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            doc_ref = collection.document(document_id)
            
            # Add update timestamp
            data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            doc_ref.set(data, merge=merge)
            logger.debug(f"Updated document {document_id} in {collection_name}")
            return True
            
        except GoogleCloudError as e:
            logger.error(f"Failed to update document {document_id} in {collection_name}: {e}")
            return False
    
    def delete_document(self, collection_name: str, document_id: str) -> bool:
        """
        Delete document with existence check
        
        Args:
            collection_name: Name of collection
            document_id: Document ID
            
        Returns:
            True if deleted, False if not found or error
        """
        try:
            collection = self.get_collection(collection_name)
            doc_ref = collection.document(document_id)
            
            doc = doc_ref.get()
            if not doc.exists:
                logger.warning(f"Document {document_id} not found for deletion in {collection_name}")
                return False
            
            doc_ref.delete()
            logger.info(f"Deleted document {document_id} from {collection_name}")
            return True
            
        except GoogleCloudError as e:
            logger.error(f"Failed to delete document {document_id} from {collection_name}: {e}")
            return False
    
    def query_collection(self, collection_name: str, 
                        field: str, operator: str, value: Any,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query collection with field filter
        
        Args:
            collection_name: Name of collection
            field: Field name to filter on
            operator: Firestore operator ('==', '>', '<', '>=', '<=', '!=', 'in', 'array_contains')
            value: Value to compare
            limit: Maximum results
            
        Returns:
            List of matching documents
        """
        try:
            collection = self.get_collection(collection_name)
            query = collection.where(field, operator, value).limit(limit)
            
            results = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)
            
            logger.debug(f"Query {collection_name} {field} {operator} {value}: {len(results)} results")
            return results
            
        except GoogleCloudError as e:
            logger.error(f"Failed to query {collection_name}: {e}")
            return []
    
    def transaction(self, max_attempts: int = 3):
        """
        Context manager for Firestore transactions with retry
        
        Args:
            max_attempts: Maximum retry attempts
            
        Yields:
            Firestore transaction object
        """
        attempt = 0
        while attempt < max_attempts:
            try:
                @firestore.transactional
                def run_transaction(transaction):
                    return transaction
                
                transaction = run_transaction(self._db.transaction())
                yield transaction
                return
                
            except GoogleCloudError as e:
                attempt += 1
                logger.warning(f"Transaction attempt {attempt} failed: {e}")
                if attempt == max_attempts:
                    logger.error(f"Transaction failed after {max_attempts} attempts")
                    raise
    
    def close(self) -> None:
        """Cleanup Firebase resources"""
        try:
            if self._app:
                firebase_admin.delete_app(self._app)
                self._app = None
                self._db = None
                self