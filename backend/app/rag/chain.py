"""RAG chain for question answering with citations"""

from typing import List, Dict, Any, Optional
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.schema import Document, BaseMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_community.llms import HuggingFacePipeline
from langchain.chains.question_answering import load_qa_chain

from app.core.config import settings
from app.rag.retriever import retriever_manager


class RAGChain:
    """RAG Chain for conversational question answering with citations"""
    
    # Shared prompt template - used by both chain methods
    SCOPE_AND_INSTRUCTIONS = """You are a specialized AI assistant for vision research and ophthalmology, trained exclusively on PubMed scientific literature.

Your role is to provide accurate, evidence-based answers using ONLY information from peer-reviewed research papers in the PubMed database.

SCOPE: You can ONLY answer questions related to:

**Eye Anatomy & Biology:**
- Eye structure (cornea, lens, retina, choroid, sclera, iris, pupil, vitreous, optic nerve)
- Photoreceptors (rods, cones, photopigments, phototransduction)
- Retinal cells (ganglion cells, bipolar cells, horizontal cells, amacrine cells, Müller cells)
- Visual pathways (optic nerve, optic chiasm, lateral geniculate nucleus, visual cortex)
- Eye development and embryology
- Ocular blood supply and vascular system

**Vision & Visual Processing:**
- Visual perception and cognition
- Color vision and color blindness
- Visual acuity and refractive errors (myopia, hyperopia, astigmatism, presbyopia)
- Accommodation and pupillary responses
- Visual fields and perimetry
- Binocular vision and stereopsis
- Motion perception and visual tracking

**Retinal Diseases & Disorders:**
- Age-related macular degeneration (AMD, wet/dry AMD, geographic atrophy)
- Diabetic retinopathy and diabetic macular edema
- Retinitis pigmentosa and inherited retinal dystrophies
- Retinal detachment and tears
- Macular holes and epiretinal membranes
- Central serous chorioretinopathy (CSC)
- Retinal vein/artery occlusions (retinal artery occlusion, retinal vein occlusion)
- Retinopathy of prematurity (ROP)
- Choroideremia and choroidal diseases
- Choroidal neovascularization
- Retinal degeneration and retinal dystrophy
- Retinal inflammation and retinal vascular disease

**Inherited Retinal Diseases:**
- Leber congenital amaurosis (LCA)
- Stargardt disease
- Best disease
- X-linked retinoschisis
- Cone-rod dystrophy
- Coats disease

**Glaucoma:**
- Primary open-angle glaucoma and angle-closure glaucoma
- Normal-tension glaucoma
- Secondary glaucoma
- Congenital glaucoma
- Neovascular glaucoma
- Intraocular pressure (IOP) and aqueous humor dynamics
- Optic nerve head damage and cupping
- Retinal ganglion cells
- Visual field loss in glaucoma
- Glaucoma treatments and surgeries

**Corneal Conditions:**
- Keratoconus and corneal ectasia
- Corneal dystrophies (Fuchs endothelial corneal dystrophy, lattice, granular)
- Corneal ulcers and infections (bacterial keratitis, fungal keratitis)
- Dry eye disease and tear film disorders (keratoconjunctivitis sicca)
- Meibomian gland dysfunction
- Corneal transplantation and keratoplasty
- Corneal wound healing and regeneration

**Lens & Cataract:**
- Cataract formation and types
- Age-related lens changes
- Congenital cataracts
- Cataract surgery (phacoemulsification) and intraocular lenses (IOLs)
- Posterior capsule opacification (PCO)

**Optic Nerve & Neuro-Ophthalmology:**
- Optic neuritis and optic neuropathy
- Papilledema and optic disc swelling
- Ischemic optic neuropathy (AION, NAION)
- Leber's hereditary optic neuropathy (LHON)
- Optic atrophy
- Visual pathway lesions
- Idiopathic intracranial hypertension

**Ocular Inflammation & Immune:**
- Uveitis (anterior uveitis, intermediate, posterior uveitis, panuveitis)
- Behcet uveitis
- Sarcoid uveitis
- Scleritis and episcleritis
- Ocular autoimmune diseases
- Inflammatory eye conditions

**Genetics & Molecular Biology:**
- Inherited eye diseases and genetic mutations
- Gene therapy for eye diseases (RPE65, CEP290, RPGR, etc.)
- CRISPR and genome editing for vision disorders
- Stem cell therapy for retinal diseases
- Optogenetics for vision restoration

**Treatments & Therapeutics:**
- Anti-VEGF therapy (ranibizumab, bevacizumab, aflibercept, faricimab)
- Photodynamic therapy
- Pars plana vitrectomy
- Complement inhibition for AMD
- Corticosteroids and immunosuppressants
- Neuroprotection strategies
- Drug delivery systems (intravitreal, topical, sustained-release)
- Retinal prosthetics and bionic eyes
- Vision rehabilitation

**Diagnostic Techniques:**
- Optical coherence tomography (OCT)
- OCT angiography (OCT-A)
- Fundus photography and fundus autofluorescence
- Fluorescein angiography and indocyanine green angiography
- Electroretinography (ERG) and electro-oculography (EOG)
- Visual field testing and perimetry
- Adaptive optics imaging

**Refractive Surgery:**
- LASIK, PRK, SMILE procedures
- Phakic IOLs
- Refractive lens exchange
- Corneal crosslinking

**Ocular Oncology:**
- Uveal melanoma and choroidal melanoma
- Retinoblastoma
- Ocular lymphoma
- Choroidal nevus

**Other Eye Conditions:**
- Amblyopia (lazy eye)
- Strabismus (eye misalignment)
- Nystagmus
- Ocular trauma and injuries

**Public Health & Vision Care:**
- Low vision and blindness
- Low vision rehabilitation
- Vision screening
- Blindness epidemiology
- Visual impairment prevalence

- Any other eye/vision-related medical or scientific topics

OUT OF SCOPE DETECTION:
- If the question is about people, biographies, non-medical topics, general knowledge, or anything NOT related to eye/vision research, you MUST respond EXACTLY with: "OUT_OF_SCOPE"
- Do NOT try to answer questions about specific people, universities, or topics unrelated to vision/eye research
- Do NOT provide any other text if the question is out of scope, just respond with: "OUT_OF_SCOPE"

IMPORTANT INSTRUCTIONS:
- Write a natural, comprehensive response based on the scientific context provided below
- DO NOT include any source citations, reference numbers, or [Source N] markers in your answer text
- DO NOT mention "Source 1", "Source 2", etc. anywhere in your response
- DO NOT write [1], [2], or any numbered references in the text
- The citations will be displayed automatically at the end, so focus on writing a clear, flowing explanation
- Only state facts that are directly supported by the provided PubMed literature context
- If the context doesn't contain information to answer a vision-related question, say so honestly
- If the user asks a follow-up question (like "what is special about it?", "tell me more", "why?"), use the Chat History to understand what they're referring to
- Resolve pronouns like "it", "this", "that" by looking at the Chat History context"""
    
    def __init__(self):
        self.llm = None
        self.retriever = None
        self.memory = None
        self.chain = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure the chain is initialized"""
        if not self._initialized:
            self.llm = self._initialize_llm()
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            self._initialized = True
    
    def _initialize_llm(self):
        """Initialize the language model"""
        if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            return ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=settings.TEMPERATURE,
                max_tokens=settings.MAX_TOKENS,
                openai_api_key=settings.OPENAI_API_KEY
            )
        elif settings.LLM_PROVIDER == "local":
            # Local LLM using OpenAI-compatible API (TGI, vLLM, llama.cpp)
            return ChatOpenAI(
                model=settings.LOCAL_LLM_MODEL,
                temperature=settings.TEMPERATURE,
                max_tokens=settings.MAX_TOKENS,
                openai_api_key=settings.LOCAL_LLM_API_KEY,
                openai_api_base=settings.LOCAL_LLM_BASE_URL,
                model_kwargs={
                    "top_p": settings.TOP_P,
                }
            )
        else:
            # Fallback: Local LLM using HuggingFace Pipeline (slower, but works without server)
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
            
            tokenizer = AutoTokenizer.from_pretrained(settings.LOCAL_LLM_MODEL)
            model = AutoModelForCausalLM.from_pretrained(
                settings.LOCAL_LLM_MODEL,
                device_map=settings.LOCAL_LLM_DEVICE
            )
            
            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=settings.MAX_TOKENS,
                temperature=settings.TEMPERATURE,
                top_p=settings.TOP_P
            )
            
            return HuggingFacePipeline(pipeline=pipe)
    
    def create_chain(
        self,
        collection_names: List[str],
        chat_history: Optional[List[tuple]] = None
    ):
        """
        Create a conversational retrieval chain
        
        Args:
            collection_names: List of collection names to search
            chat_history: Optional chat history
        """
        # Create retriever for multiple collections
        if len(collection_names) == 1:
            self.retriever = retriever_manager.get_basic_retriever(collection_names[0])
        else:
            # For multiple collections, we'll handle this in the query method
            self.retriever = retriever_manager.get_basic_retriever(collection_names[0])
        
        # Create memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        # Add existing chat history if provided
        if chat_history:
            for human, ai in chat_history:
                self.memory.chat_memory.add_user_message(human)
                self.memory.chat_memory.add_ai_message(ai)
        
        # Create custom prompt using shared template
        prompt_template = f"""{self.SCOPE_AND_INSTRUCTIONS}

Context from PubMed research papers:
{{context}}

Chat History:
{{chat_history}}

Question: {{question}}

First, determine if this question is related to eye/vision research. If NOT, respond with EXACTLY: "OUT_OF_SCOPE"

If it IS related to vision/eye research, provide a detailed, scientifically accurate answer based solely on the PubMed literature context above:

Answer:"""
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "chat_history", "question"]
        )
        
        # Create chain
        self.chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever,
            memory=self.memory,
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": PROMPT},
            verbose=True
        )
    
    def query(
        self,
        question: str,
        collection_names: Optional[List[str]] = None,
        chat_history: Optional[List[tuple]] = None
    ) -> Dict[str, Any]:
        """
        Query the RAG chain
        
        Args:
            question: User question
            collection_names: Optional list of collections to search
            chat_history: Optional chat history
            
        Returns:
            Dictionary with answer and source documents
        """
        # Create chain if not exists or if collection changed
        if self.chain is None:
            if not collection_names:
                collection_names = ["pubmed_abstracts"]
            self.create_chain(collection_names, chat_history)
        
        # Query the chain
        result = self.chain({"question": question})
        
        # Extract answer and sources
        answer = result["answer"]
        source_documents = result.get("source_documents", [])
        
        # Format citations
        citations = self._format_citations(source_documents)
        
        return {
            "answer": answer,
            "source_documents": source_documents,
            "citations": citations
        }
    
    def _is_vision_related(self, question: str) -> bool:
        """
        Check if question is related to vision/eye research using keyword matching
        
        Args:
            question: User question
            
        Returns:
            True if vision-related, False otherwise
        """
        question_lower = question.lower()
        
        # Vision-related keywords
        vision_keywords = [
            # Eye anatomy
            'eye', 'eyes', 'retina', 'retinal', 'cornea', 'corneal', 'lens', 'iris', 'pupil',
            'macula', 'macular', 'fovea', 'optic nerve', 'choroid', 'sclera', 'vitreous',
            'photoreceptor', 'rod', 'cone', 'ganglion',
            
            # Vision terms
            'vision', 'visual', 'sight', 'seeing', 'blind', 'blindness', 'low vision',
            'visual acuity', 'visual field', 'visual impairment',
            
            # Eye diseases
            'amd', 'macular degeneration', 'glaucoma', 'cataract', 'diabetic retinopathy',
            'retinopathy', 'retinitis pigmentosa', 'uveitis', 'keratoconus', 'dry eye',
            'stargardt', 'leber', 'choroideremia', 'retinal detachment', 'macular hole',
            'epiretinal membrane', 'drusen', 'geographic atrophy', 'keratitis',
            
            # Treatments
            'anti-vegf', 'ranibizumab', 'aflibercept', 'bevacizumab', 'lucentis', 'eylea',
            'vitrectomy', 'lasik', 'cataract surgery', 'corneal transplant',
            
            # Imaging
            'oct', 'optical coherence tomography', 'fundus', 'angiography', 'fluorescein',
            'autofluorescence', 'ophthalmoscopy', 'perimetry',
            
            # Medical terms
            'ophthalmology', 'ophthalmologist', 'optometry', 'optometrist', 'intraocular',
            'ocular', 'ophthalmic'
        ]
        
        # Check if any vision keyword is in the question
        for keyword in vision_keywords:
            if keyword in question_lower:
                return True
        
        return False
    
    def query_with_custom_retrieval(
        self,
        question: str,
        collection_names: List[str],
        k: int = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Query with custom retrieval from multiple collections
        
        Args:
            question: User question
            collection_names: List of collections to search
            k: Number of documents to retrieve
            chat_history: Optional chat history
            
        Returns:
            Dictionary with answer and source documents
        """
        # Ensure LLM is initialized
        self._ensure_initialized()
        
        k = k or settings.RETRIEVAL_K
        
        # Use advanced retrieval: fetch more docs initially for better reranking
        fetch_k = k * 3  # Fetch 3x more documents for reranking
        
        # Retrieve documents with scores from all collections using MMR for diversity
        docs_with_scores = []
        for collection_name in collection_names:
            try:
                # Use MMR retriever for better diversity
                mmr_retriever = retriever_manager.get_mmr_retriever(
                    collection_name=collection_name,
                    k=k,
                    fetch_k=fetch_k,
                    lambda_mult=0.7  # Balance between relevance (0.7) and diversity (0.3)
                )
                
                # Get documents with MMR
                mmr_docs = mmr_retriever.get_relevant_documents(question)
                
                # Get scores for these documents
                scored_results = retriever_manager.retrieve_with_scores(
                    query=question,
                    collection_name=collection_name,
                    k=fetch_k
                )
                
                # Create a score map
                score_map = {doc.page_content: score for doc, score in scored_results}
                
                # Add scores to MMR docs
                for doc in mmr_docs:
                    score = score_map.get(doc.page_content, 1.0)
                    docs_with_scores.append((doc, score))
                    
            except Exception as e:
                print(f"Error with MMR retriever for {collection_name}: {e}")
                # Fallback to regular retrieval
                results = retriever_manager.retrieve_with_scores(
                    query=question,
                    collection_name=collection_name,
                    k=k
                )
                docs_with_scores.extend(results)
        
        # Sort by score (lower distance is better)
        docs_with_scores.sort(key=lambda x: x[1])
        
        # Take top k overall after reranking
        docs_with_scores = docs_with_scores[:k]
        
        # Extract documents and store scores in metadata
        retrieved_docs = []
        for doc, score in docs_with_scores:
            # Add score to metadata
            doc.metadata['score'] = score
            retrieved_docs.append(doc)
        
        # Format chat history for prompt
        chat_history_text = ""
        if chat_history:
            for msg in chat_history[-5:]:  # Last 5 messages
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    chat_history_text += f"Human: {content}\n"
                elif role == "assistant":
                    chat_history_text += f"Assistant: {content}\n"
        
        # Create context from retrieved documents
        context = "\n\n".join([
            f"[Source {i+1}]: {doc.page_content}"
            for i, doc in enumerate(retrieved_docs)
        ])
        
        # Create prompt using shared template
        prompt = f"""You are a specialized AI assistant for vision research and ophthalmology. You can ONLY answer questions about:
- Eye diseases, anatomy, and physiology
- Vision disorders and treatments  
- Ophthalmology and optometry
- Eye-related genetics and research

Context from PubMed research papers:
{context}

Chat History:
{chat_history_text}

Question: {question}

INSTRUCTIONS:
Step 1: First, determine if this question is about eye/vision/ophthalmology topics.
- If YES (e.g., "what is retina", "AMD treatment", "glaucoma symptoms"): Proceed to Step 2
- If NO (e.g., "who is Tony Stark", "capital of France", "how to cook pasta"): Respond with EXACTLY "OUT_OF_SCOPE" and nothing else

Step 2: If the question IS about eye/vision topics, provide a detailed answer using ONLY the PubMed research context above. Do not make up information.

Your response:"""
        
        # Get response from LLM
        try:
            if hasattr(self.llm, 'predict'):
                answer = self.llm.predict(prompt)
            elif hasattr(self.llm, 'invoke'):
                # For newer LangChain versions
                response = self.llm.invoke(prompt)
                # Extract content if it's a message object
                answer = response.content if hasattr(response, 'content') else str(response)
            else:
                answer = self.llm(prompt)
        except Exception as e:
            print(f"Error calling LLM: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Format citations
        citations = self._format_citations(retrieved_docs)
        
        return {
            "answer": answer,
            "source_documents": retrieved_docs,
            "citations": citations
        }
    
    def _format_citations(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        Format source documents into citation objects
        
        Args:
            documents: List of source documents
            
        Returns:
            List of citation dictionaries
        """
        citations = []
        
        for i, doc in enumerate(documents):
            metadata = doc.metadata
            pmid = metadata.get("pmid")
            
            # Construct PubMed URL if PMID exists
            url = metadata.get("url")
            if not url and pmid:
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            
            # Convert distance score to relevance score (0-1, higher is better)
            # ChromaDB returns L2 distance, where lower is better
            # Convert to similarity: relevance = 1 / (1 + distance)
            distance = metadata.get("score", 1.0)
            relevance_score = 1.0 / (1.0 + distance) if distance is not None else 0.5
            
            citation = {
                "source_type": "pubmed",
                "source_id": pmid or metadata.get("source"),
                "title": metadata.get("title", "Untitled"),
                "authors": metadata.get("authors"),
                "journal": metadata.get("journal"),
                "publication_date": metadata.get("publication_date"),
                "url": url,
                "excerpt": doc.page_content[:500],  # First 500 chars
                "relevance_score": round(relevance_score, 3)
            }
            
            citations.append(citation)
        
        return citations
    
    def clear_memory(self):
        """Clear conversation memory"""
        if self.memory:
            self.memory.clear()


# Global RAG chain instance - lazy loaded
rag_chain = None

def get_rag_chain():
    """Get or create RAG chain instance"""
    global rag_chain
    if rag_chain is None:
        rag_chain = RAGChain()
    return rag_chain

