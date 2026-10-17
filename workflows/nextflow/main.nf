#!/usr/bin/env nextflow
// Prototype workflow wrapping repository scripts. Validated statically only (see docs/reproducibility.md).
nextflow.enable.dsl = 2

params.csv      = null            // labelled CSV; omit with --demo true to use SYNTHETIC data
params.demo     = false
params.target   = 'label'
params.group    = 'group'
params.seed     = 42
params.outdir   = 'results'

process TRAIN_MODEL {
    publishDir params.outdir, mode: 'copy'
    cpus 1
    memory '2 GB'

    input:
    path csv

    output:
    path 'model/*', emit: artifact
    path 'report.json', emit: report

    script:
    def src = params.demo ? '--demo' : "--csv ${csv}"
    """
    python ${projectDir}/../../scripts/train_model.py ${src} --target ${params.target} \\
        --group-column ${params.group} --seed ${params.seed} --out model --report report.json
    """
}

workflow {
    if (!params.demo && !params.csv) {
        error "Provide --csv <file> or --demo true"
    }

    if (params.demo) {
        input_ch = Channel.value(file("${projectDir}/nextflow.config"))
    } else {
        input_ch = Channel.value(file(params.csv, checkIfExists: true))
    }

    TRAIN_MODEL(input_ch)
}
