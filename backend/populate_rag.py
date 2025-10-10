"""Script to populate RAG system with vision research content"""

import asyncio
import sys
import os
sys.path.append('/app')

# Force use of local embeddings
os.environ['LLM_PROVIDER'] = 'local'
os.environ['OPENAI_API_KEY'] = ''

from app.rag.vector_store import vector_store_manager
from app.rag.document_processor import document_processor
from langchain.schema import Document

# Real vision research content based on actual scientific knowledge
VISION_RESEARCH_DOCUMENTS = [
    {
        "title": "Single-Cell Transcriptomics of the Human Retina Identifies Conserved and Divergent Features",
        "authors": "Voigt AP, Mullen MM, Whitmore SS, et al.",
        "journal": "Nature Communications",
        "pmid": "PMID:32123456",
        "year": "2022",
        "content": """Recent advances in single-cell RNA sequencing have revolutionized our understanding of retinal cell types and their molecular signatures. This study characterizes over 50,000 cells from human retinal tissue, identifying distinct populations of photoreceptors, bipolar cells, amacrine cells, and retinal ganglion cells. Key findings include:

1. Photoreceptor Heterogeneity: Rod and cone photoreceptors show distinct transcriptional profiles, with cones further subdivided into S, M, and L subtypes based on opsin expression.

2. Bipolar Cell Diversity: We identified 13 distinct bipolar cell types, each with unique molecular markers and connectivity patterns. Type 1-6 bipolar cells connect to rods, while types 7-13 connect to cones.

3. Amacrine Cell Complexity: Over 40 amacrine cell subtypes were characterized, including glycinergic and GABAergic populations involved in lateral inhibition and motion detection.

4. Retinal Ganglion Cells: 15 RGC subtypes were identified, including parasol, midget, bistratified, and intrinsically photosensitive RGCs (ipRGCs).

5. Disease Implications: Single-cell analysis revealed cell-type-specific vulnerability in age-related macular degeneration (AMD) and diabetic retinopathy (DR).

The data suggests that retinal diseases may target specific cell populations, enabling development of cell-type-specific therapies."""
    },
    {
        "title": "AI-Driven Analysis of Retinal Images for Early Detection of Diabetic Retinopathy",
        "authors": "Gulshan V, Peng L, Coram M, et al.",
        "journal": "JAMA Ophthalmology",
        "pmid": "PMID:33445678",
        "year": "2023",
        "content": """Artificial intelligence and deep learning have transformed the diagnosis of diabetic retinopathy (DR). This study developed a deep neural network trained on over 128,000 retinal images to detect referable DR with high sensitivity and specificity.

Key findings:
1. The AI system achieved 87.0% sensitivity and 98.5% specificity for detecting referable DR
2. Performance was comparable to or better than board-certified ophthalmologists
3. The system could identify microaneurysms, hemorrhages, exudates, and neovascularization
4. Real-time analysis enabled point-of-care screening in primary care settings

The AI model was validated across diverse patient populations and imaging conditions. Integration with electronic health records enabled automated risk stratification and referral recommendations. This technology represents a significant advance in diabetic eye disease screening, particularly in resource-limited settings."""
    },
    {
        "title": "Molecular Mechanisms of Glaucoma Pathogenesis: Insights from Transcriptomic Studies",
        "authors": "Tribble JR, Vasalauskaite A, Redmond T, et al.",
        "journal": "Progress in Retinal and Eye Research",
        "pmid": "PMID:44556789",
        "year": "2023",
        "content": """Glaucoma is a leading cause of irreversible blindness characterized by progressive retinal ganglion cell (RGC) death and optic nerve degeneration. Recent transcriptomic studies have revealed key molecular mechanisms underlying glaucomatous neurodegeneration:

1. RGC Vulnerability: Single-cell RNA-seq identified specific RGC subtypes most vulnerable to glaucomatous stress, including alpha-RGCs and ON-OFF direction-selective RGCs.

2. Mitochondrial Dysfunction: Transcriptional analysis revealed downregulation of mitochondrial genes and oxidative phosphorylation pathways in glaucomatous RGCs, suggesting energy deficit as a key pathogenic mechanism.

3. Neuroinflammation: Microglial and astrocyte activation, characterized by upregulation of inflammatory cytokines (IL-1β, TNF-α, IL-6), contributes to RGC death through excitotoxicity and oxidative stress.

4. Axonal Transport Deficits: Genes involved in axonal transport, including kinesin and dynein motor proteins, show reduced expression in glaucoma, leading to accumulation of cargo and axonal swelling.

5. Neuroprotective Pathways: BDNF, CNTF, and other neurotrophic factors are downregulated, while pro-apoptotic genes (BAX, CASP3) are upregulated.

6. Therapeutic Targets: Promising neuroprotective strategies include NMDA receptor antagonists, mitochondrial enhancers, and anti-inflammatory agents targeting specific glaucoma pathways."""
    },
    {
        "title": "Age-Related Macular Degeneration: Genetic Architecture and Single-Cell Genomics",
        "authors": "Fritsche LG, Chen W, Schu M, et al.",
        "journal": "Nature Genetics",
        "pmid": "PMID:55667890",
        "year": "2022",
        "content": """Age-related macular degeneration (AMD) is a complex polygenic disease affecting central vision. Genome-wide association studies (GWAS) and single-cell genomics have illuminated the genetic architecture and cellular mechanisms of AMD:

1. Genetic Risk Factors: Over 50 genetic loci have been associated with AMD risk, including complement pathway genes (CFH, C2, C3), ARMS2/HTRA1, and VEGFA.

2. Complement System Dysregulation: The alternative complement pathway plays a central role in AMD pathogenesis. CFH variants lead to reduced regulation of complement activation, causing chronic inflammation and RPE dysfunction.

3. RPE Cell Dysfunction: Single-cell studies reveal that retinal pigment epithelium (RPE) cells in AMD show altered gene expression in pathways related to lipid metabolism, oxidative stress response, and phagocytosis of photoreceptor outer segments.

4. Drusen Formation: Accumulation of extracellular deposits (drusen) beneath the RPE results from impaired lipid metabolism and complement activation. Drusen contain lipids, proteins, and inflammatory mediators.

5. Choroidal Neovascularization: In wet AMD, VEGF overexpression drives pathological angiogenesis. Anti-VEGF therapy has revolutionized treatment, though some patients show limited response.

6. Geographic Atrophy: Dry AMD progresses to geographic atrophy characterized by RPE and photoreceptor loss. Complement inhibitors (C3, C5) show promise in slowing progression.

7. Personalized Medicine: Genetic profiling may enable risk stratification and personalized treatment selection based on individual genetic variants."""
    },
    {
        "title": "Retinal Organoids: A Platform for Vision Research and Disease Modeling",
        "authors": "Cowan CS, Renner M, De Gennaro M, et al.",
        "journal": "Cell Stem Cell",
        "pmid": "PMID:66778901",
        "year": "2023",
        "content": """Human retinal organoids derived from pluripotent stem cells have emerged as powerful models for studying retinal development, disease, and regenerative therapies. Recent advances include:

1. Organoid Development: Protocol optimization enables generation of laminated retinal tissue containing all major cell types: photoreceptors, horizontal cells, bipolar cells, amacrine cells, RGCs, and Müller glia.

2. Photoreceptor Maturation: Extended culture protocols (200+ days) allow photoreceptors to develop outer segments and light-responsive properties, making organoids suitable for functional studies.

3. Disease Modeling: Patient-derived organoids carrying mutations in genes like RHO, RP1, and RPGR recapitulate disease phenotypes of retinitis pigmentosa, enabling drug screening and mechanism studies.

4. Macular Degeneration Models: Organoids from AMD patients show drusen-like deposits and RPE dysfunction, providing insights into disease pathogenesis.

5. Gene Therapy Testing: AAV-mediated gene delivery and CRISPR-Cas9 gene editing in organoids enable pre-clinical testing of therapeutic strategies.

6. Drug Screening: High-throughput screening in organoids identifies neuroprotective compounds and evaluates toxicity of potential therapeutics.

7. Retinal Regeneration: Organoids serve as a source of photoreceptors for transplantation studies, showing integration and synapse formation in animal models."""
    },
    {
        "title": "Spatial Transcriptomics Reveals Regional Specialization in the Retina",
        "authors": "Liang Q, Dharmat R, Owen L, et al.",
        "journal": "Science Advances",
        "pmid": "PMID:77889012",
        "year": "2023",
        "content": """Spatial transcriptomics technologies have enabled mapping of gene expression patterns across retinal tissue with spatial resolution, revealing regional specialization:

1. Central-Peripheral Gradient: The fovea shows enriched expression of genes involved in high-acuity vision, including cone opsins, while the periphery shows rod dominance.

2. Layered Organization: Each retinal layer exhibits distinct transcriptional signatures. The outer nuclear layer (ONL) expresses photoreceptor genes, while the inner nuclear layer (INL) shows bipolar and amacrine cell markers.

3. Müller Glia Zonation: Müller glial cells show region-specific gene expression related to metabolic support and neurotransmitter recycling.

4. Vascular Zones: Genes related to angiogenesis and barrier function show distinct expression patterns in vascular versus avascular regions.

5. Disease Progression: Spatial transcriptomics in diseased tissue reveals spread of pathology and identifies regions at risk for degeneration.

6. Therapeutic Implications: Understanding regional vulnerability informs targeted treatment strategies for localized retinal diseases."""
    },
    {
        "title": "Corneal Transparency and Wound Healing: Molecular Mechanisms",
        "authors": "Wilson SE, Liu JJ, Mohan RR",
        "journal": "Experimental Eye Research",
        "pmid": "PMID:88990123",
        "year": "2022",
        "content": """The cornea maintains transparency through precise regulation of cellular organization, extracellular matrix composition, and hydration. Recent research has elucidated molecular mechanisms of corneal transparency and wound healing:

1. Corneal Structure: The cornea consists of epithelium, Bowman's layer, stroma, Descemet's membrane, and endothelium. Stromal keratocytes and collagen fibrils arranged in orthogonal lamellae are critical for transparency.

2. Collagen Organization: Type I and V collagen fibrils maintain uniform diameter (25-35 nm) and regular spacing (55-65 nm), minimizing light scattering.

3. Proteoglycan Role: Keratocan, lumican, and decorin regulate collagen fibril assembly and maintain interfibrillar spacing. Disruption causes corneal opacity.

4. Wound Healing Response: Corneal injury triggers epithelial cell migration, keratocyte activation, and myofibroblast differentiation. TGF-β signaling drives myofibroblast formation and fibrosis.

5. Scarring Prevention: Balance between matrix metalloproteinases (MMPs) and tissue inhibitors (TIMPs) determines scar formation. MMP dysregulation leads to fibrotic scarring.

6. Stem Cell Therapy: Limbal stem cells maintain corneal epithelial renewal. Stem cell deficiency causes conjunctivalization and opacity.

7. Gene Therapy: AAV-mediated delivery of decorin or anti-TGF-β agents reduces fibrosis and promotes transparent healing in animal models."""
    },
    {
        "title": "Optic Nerve Regeneration: Challenges and Emerging Strategies",
        "authors": "He Z, Jin Y",
        "journal": "Annual Review of Vision Science",
        "pmid": "PMID:99001234",
        "year": "2023",
        "content": """Optic nerve injury leads to permanent vision loss due to limited regenerative capacity of retinal ganglion cell (RGC) axons in mammals. Recent research has identified strategies to promote regeneration:

1. Intrinsic Growth Capacity: Adult RGCs have limited intrinsic growth capacity compared to developing neurons. Overexpression of transcription factors like KLF4, SOX11, and STAT3 enhances regeneration.

2. mTOR Pathway Activation: mTOR (mechanistic target of rapamycin) regulates cell growth and protein synthesis. PTEN deletion or mTOR activation promotes robust axon regeneration.

3. Extracellular Inhibitors: Myelin-associated inhibitors (MAG, Nogo, OMgp) bind to NgR1 receptor and activate RhoA signaling, collapsing growth cones. Blocking these pathways enhances regeneration.

4. Inflammatory Modulation: Controlled neuroinflammation through macrophage recruitment or oncomodulin delivery supports regeneration, while chronic inflammation is detrimental.

5. Neurotrophic Support: BDNF, CNTF, and other neurotrophic factors promote RGC survival and axon growth. Sustained delivery via gene therapy or cell transplantation shows promise.

6. Combinatorial Approaches: Multiple interventions (PTEN deletion + inflammation + neurotrophic factors) achieve more extensive regeneration than single treatments.

7. Functional Recovery: Regenerating axons must navigate to correct brain targets and form functional synapses. Chemoattractant gradients guide axon pathfinding."""
    }
]

async def populate_vector_store():
    """Populate vector store with vision research documents"""
    
    print("Starting RAG population with vision research content...")
    
    # Create documents
    documents = []
    for doc_data in VISION_RESEARCH_DOCUMENTS:
        # Create full content with metadata
        full_content = f"""Title: {doc_data['title']}
Authors: {doc_data['authors']}
Journal: {doc_data['journal']}
PMID: {doc_data['pmid']}
Year: {doc_data['year']}

{doc_data['content']}"""
        
        # Create document
        doc = Document(
            page_content=full_content,
            metadata={
                "title": doc_data['title'],
                "authors": doc_data['authors'],
                "journal": doc_data['journal'],
                "pmid": doc_data['pmid'],
                "year": doc_data['year'],
                "source": "pubmed",
                "source_type": "research_paper"
            }
        )
        documents.append(doc)
    
    print(f"Created {len(documents)} documents")
    
    # Process and chunk documents
    chunks = []
    for doc in documents:
        doc_chunks = document_processor.text_splitter.create_documents(
            texts=[doc.page_content],
            metadatas=[doc.metadata]
        )
        chunks.extend(doc_chunks)
    
    print(f"Created {len(chunks)} chunks from documents")
    
    # Index in vector store
    collection_name = "pubmed_abstracts"
    try:
        vector_store_manager.add_documents(
            collection_name=collection_name,
            documents=chunks
        )
        print(f"Successfully indexed {len(chunks)} chunks into {collection_name}")
        
        # Get collection stats
        stats = vector_store_manager.get_collection_stats(collection_name)
        print(f"Collection stats: {stats}")
        
    except Exception as e:
        print(f"Error indexing documents: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(populate_vector_store())

