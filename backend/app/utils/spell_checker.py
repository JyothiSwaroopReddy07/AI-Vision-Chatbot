"""
Spell checker utility for user query correction
Uses multiple strategies similar to Google's spell checker
"""

import re
from typing import Tuple, Optional, Dict, List
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class SpellChecker:
    """
    Advanced spell checker that corrects user queries before LLM processing.
    Uses multiple strategies for best results:
    1. Language Tool (grammar and spell checking - like Google)
    2. PySpellChecker (fast offline dictionary-based checking)
    3. Medical/Scientific term preservation
    """
    
    def __init__(self):
        self.language_tool = None
        self.spell_checker = None
        self.initialized = False
        
        # Medical and scientific terms that should NOT be corrected
        self.protected_terms = {
            # Eye anatomy
            'retina', 'cornea', 'sclera', 'choroid', 'iris', 'pupil', 'lens',
            'vitreous', 'macula', 'fovea', 'optic', 'photoreceptor', 'ganglion',
            'bipolar', 'amacrine', 'horizontal', 'müller', 'muller',
            
            # Diseases
            'glaucoma', 'cataract', 'keratoconus', 'uveitis', 'retinopathy',
            'maculopathy', 'dystrophy', 'myopia', 'hyperopia', 'astigmatism',
            'presbyopia', 'amblyopia', 'strabismus', 'nystagmus', 'ptosis',
            
            # Procedures and techniques
            'vitrectomy', 'phacoemulsification', 'keratoplasty', 'lasik', 
            'photocoagulation', 'cryotherapy', 'iridotomy', 'trabeculectomy',
            
            # Proteins and genes
            'vegf', 'rpe65', 'cep290', 'rpgr', 'abca4', 'rhodopsin', 'opsin',
            'crispr', 'cas9',
            
            # Imaging and diagnostics
            'oct', 'octa', 'erg', 'eog', 'vep', 'mri', 'ct',
            
            # Medications
            'ranibizumab', 'bevacizumab', 'aflibercept', 'faricimab',
            'latanoprost', 'timolol', 'brimonidine', 'dorzolamide',
            
            # Common abbreviations
            'amd', 'armd', 'rvo', 'brvo', 'crvo', 'csc', 'dme', 'pdr', 'npdr',
            'poag', 'pacg', 'iop', 'bcva', 'etdrs', 'iol'
        }
        
        # Common misspellings in medical context
        self.custom_corrections = {
            'retin': 'retina',
            'corneal': 'cornea',
            'glaucoma': 'glaucoma',
            'catract': 'cataract',
            'macular': 'macula',
        }
    
    def _initialize(self):
        """Lazy initialization of spell checkers"""
        if self.initialized:
            return
        
        try:
            # Try to initialize Language Tool (preferred)
            try:
                import language_tool_python
                self.language_tool = language_tool_python.LanguageTool('en-US')
                logger.info("Language Tool initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize Language Tool: {e}")
                self.language_tool = None
            
            # Initialize PySpellChecker (fallback)
            try:
                from spellchecker import SpellChecker
                self.spell_checker = SpellChecker()
                # Add protected medical terms to known words
                self.spell_checker.word_frequency.load_words(self.protected_terms)
                logger.info("PySpellChecker initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize PySpellChecker: {e}")
                self.spell_checker = None
            
            self.initialized = True
            
        except Exception as e:
            logger.error(f"Error initializing spell checkers: {e}")
            self.initialized = True  # Mark as initialized to avoid repeated attempts
    
    def _is_protected_term(self, word: str) -> bool:
        """Check if a word is a protected medical/scientific term"""
        word_lower = word.lower()
        
        # Check protected terms
        if word_lower in self.protected_terms:
            return True
        
        # Check if it's an acronym (all caps, 2-6 chars)
        if word.isupper() and 2 <= len(word) <= 6:
            return True
        
        # Check if it contains numbers (likely a medical code or reference)
        if any(char.isdigit() for char in word):
            return True
        
        return False
    
    def _preserve_case(self, original: str, corrected: str) -> str:
        """Preserve the original case pattern when correcting"""
        if original.isupper():
            return corrected.upper()
        elif original[0].isupper():
            return corrected.capitalize()
        return corrected.lower()
    
    def correct_with_language_tool(self, text: str) -> Tuple[str, List[Dict]]:
        """
        Correct text using Language Tool (grammar and spelling)
        Returns: (corrected_text, corrections_made)
        """
        if not self.language_tool:
            return text, []
        
        try:
            matches = self.language_tool.check(text)
            corrections = []
            
            # Filter out corrections for protected terms
            valid_matches = []
            for match in matches:
                word = text[match.offset:match.offset + match.errorLength]
                if not self._is_protected_term(word):
                    valid_matches.append(match)
            
            if not valid_matches:
                return text, []
            
            # Apply corrections
            corrected_text = self.language_tool.correct(text)
            
            # Track what was corrected
            for match in valid_matches:
                if match.replacements:
                    corrections.append({
                        'original': text[match.offset:match.offset + match.errorLength],
                        'corrected': match.replacements[0],
                        'type': match.ruleId
                    })
            
            return corrected_text, corrections
            
        except Exception as e:
            logger.error(f"Error with Language Tool correction: {e}")
            return text, []
    
    def correct_with_pyspellchecker(self, text: str) -> Tuple[str, List[Dict]]:
        """
        Correct text using PySpellChecker (dictionary-based)
        Returns: (corrected_text, corrections_made)
        """
        if not self.spell_checker:
            return text, []
        
        try:
            # Tokenize while preserving punctuation
            words = re.findall(r'\b\w+\b', text)
            corrections = []
            corrected_words = []
            
            for word in words:
                # Skip protected terms
                if self._is_protected_term(word):
                    corrected_words.append(word)
                    continue
                
                # Check custom corrections first
                word_lower = word.lower()
                if word_lower in self.custom_corrections:
                    correction = self.custom_corrections[word_lower]
                    correction = self._preserve_case(word, correction)
                    corrected_words.append(correction)
                    corrections.append({
                        'original': word,
                        'corrected': correction,
                        'type': 'custom'
                    })
                    continue
                
                # Get correction
                correction = self.spell_checker.correction(word)
                
                if correction and correction.lower() != word.lower():
                    # Preserve original case
                    correction = self._preserve_case(word, correction)
                    corrected_words.append(correction)
                    corrections.append({
                        'original': word,
                        'corrected': correction,
                        'type': 'dictionary'
                    })
                else:
                    corrected_words.append(word)
            
            # Reconstruct text with punctuation
            corrected_text = text
            for i, word in enumerate(words):
                if i < len(corrected_words):
                    corrected_text = re.sub(
                        r'\b' + re.escape(word) + r'\b',
                        corrected_words[i],
                        corrected_text,
                        count=1
                    )
            
            return corrected_text, corrections
            
        except Exception as e:
            logger.error(f"Error with PySpellChecker correction: {e}")
            return text, []
    
    @lru_cache(maxsize=1000)
    def correct_query(self, query: str) -> Tuple[str, List[Dict]]:
        """
        Correct spelling and grammar in user query
        
        Args:
            query: User's input query
            
        Returns:
            Tuple of (corrected_query, corrections_made)
            - corrected_query: The corrected text
            - corrections_made: List of corrections with original/corrected pairs
        """
        self._initialize()
        
        # Quick checks for queries that don't need correction
        if not query or len(query.strip()) < 2:
            return query, []
        
        # If it's just a greeting or very short, skip
        if len(query.split()) <= 2 and query.lower().strip() in [
            'hi', 'hello', 'hey', 'thanks', 'thank you', 'ok', 'okay', 'yes', 'no'
        ]:
            return query, []
        
        all_corrections = []
        corrected_query = query
        
        # Try Language Tool first (more comprehensive)
        if self.language_tool:
            corrected_query, corrections = self.correct_with_language_tool(query)
            all_corrections.extend(corrections)
            
            # If Language Tool made corrections, use that
            if corrections:
                logger.info(f"Language Tool corrections: {len(corrections)} changes")
                return corrected_query, all_corrections
        
        # Fallback to PySpellChecker
        if self.spell_checker:
            corrected_query, corrections = self.correct_with_pyspellchecker(query)
            all_corrections.extend(corrections)
            
            if corrections:
                logger.info(f"PySpellChecker corrections: {len(corrections)} changes")
        
        return corrected_query, all_corrections
    
    def get_suggestions(self, word: str, max_suggestions: int = 5) -> List[str]:
        """
        Get spelling suggestions for a single word
        
        Args:
            word: Word to get suggestions for
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of suggested corrections
        """
        self._initialize()
        
        if self._is_protected_term(word):
            return [word]
        
        suggestions = []
        
        # Try PySpellChecker
        if self.spell_checker:
            try:
                candidates = self.spell_checker.candidates(word)
                if candidates:
                    suggestions.extend(list(candidates)[:max_suggestions])
            except Exception as e:
                logger.error(f"Error getting suggestions: {e}")
        
        return suggestions[:max_suggestions]
    
    def clear_cache(self):
        """Clear the correction cache"""
        self.correct_query.cache_clear()


# Global spell checker instance
_spell_checker = None


def get_spell_checker() -> SpellChecker:
    """Get or create the global spell checker instance"""
    global _spell_checker
    if _spell_checker is None:
        _spell_checker = SpellChecker()
    return _spell_checker


def correct_user_query(query: str) -> Tuple[str, List[Dict]]:
    """
    Convenience function to correct a user query
    
    Args:
        query: User's input query
        
    Returns:
        Tuple of (corrected_query, corrections_made)
    """
    checker = get_spell_checker()
    return checker.correct_query(query)

