#!/usr/bin/env nextflow
/*
 * ==============================================================================
 * Reproducible Genomic Pipeline: QC and Alignment
 * Author: Sudheer K. Mohammed
 * ==============================================================================
 */

nextflow.enable.dsl=2

process FASTQC {
    tag "$sample_id"
    container 'quay.io/biocontainers/fastqc:0.12.1--hdfd78af_0'
    publishDir "${params.outdir}/fastqc", mode: 'copy'

    input:
    tuple val(sample_id), path(reads)

    output:
    path "*_fastqc.{zip,html}", emit: qc_reports

    script:
    """
    echo "Running FastQC on $sample_id inside $(hostname)..."
    fastqc -q ${reads}
    """
}

process SAMTOOLS_VERSION {
    tag "version_check"
    container 'quay.io/biocontainers/samtools:1.19.2--h50ea8bc_1'
    publishDir "${params.outdir}/version", mode: 'copy'

    output:
    path "samtools_version.txt"

    script:
    """
    samtools --version > samtools_version.txt
    """
}

workflow {
    read_pairs_ch = Channel.fromFilePairs(params.reads, checkIfExists: false)
    
    // Demonstrate containerized step execution
    SAMTOOLS_VERSION()
    FASTQC(read_pairs_ch)
}
