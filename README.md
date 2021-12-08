# Análisis metataxonómico (gen 16S rRNA) de secuencias generadas usando la tecnología MinION

Última actualización: 10 de mayo de 2020

Este pipeline se basa en el uso de BLAST (dentro de la interfaz de [QIIME](http://qiime.org/)) para asignar la taxonomía a cada una de las secuencias generadas por MinION (o cualquier otra plataforma de *[Oxford Nanopore Technologies](https://nanoporetech.com/)*; ONT)

*Nota*: mantengo este repositorio por reproducibilidad, aunque el protocolo [Spaghetti](https://github.com/adlape95/Spaghetti) es más recomendable generalmente para este tipo de análisis.

## 1. Preprocesamiento de datos

El primer paso para el análisis metataxonómico es el preprocesamiento de datos. Para ello hay que seguir las siguientes indicaciones:

### Eliminación de adaptadores

Se usa la herramienta [Porechop](https://github.com/rrwick/Porechop), ejecutando el siguiente comando:

```{bash}
porechop -t number_of_threads -i input_file.fastq -o input_file-porechop.fastq
```

(Repetir el proceso para cada archivo/muestra)

### Filtrado por tamaño

```{bash}
cat input_file-porechop.fastq | NanoFilt -l 700 --maxlength 1700 > input_file-porechop-nanofilt.fastq
```

En este caso, se eliminan las secuencias con un tamaño menor a 700 pb o mayor a 1700 pb

### Eliminación de quimeras (opcional)

Se ejecuta software [yacrd](https://github.com/natir/yacrd) con los parámetros por defecto

```{bash}
minimap2 -x ava-ont -g 500 -t number_of_threads input_file-porechop-nanofilt.fastq input_file-porechop-nanofilt.fastq > input_file-porechop-nanofilt.paf
yacrd -i input_file-porechop-nanofilt.paf -o input_file-porechop-nanofilt.yacrd -c 4 -n 0.4 scrubb -i input_file-porechop-nanofilt.fastq -o input_file-porechop-nanofilt.scrubb.fastq
rm *.paf
```

Una vez concluido este paso, ya tendríamos listas las secuencias para la asignación taxonómica con QIIME+BLAST.

QIIME es una herramienta de análisis de amplicones, especialmente diseñada para trabajar con secuencias derivadas del gen 16S rRNA. Hoy en día, la versión recomendada de QIIME es [QIIME 2](https://qiime2.org/). No obstante, QIIME 2 está altamente optimizado para datos de Illumina, haciendo muy difícil el análisis de secuencias ONT o PacBio. Por ello, siempre que secuenciamos con plataformas ONT (p.e. MinION) hacemos uso de la primera versión de [QIIME](http://qiime.org/).

## 2. Installación de QIIME

Lo mejor es hacerlo a través de conda como se indica [aquí](http://qiime.org/install/install.html).

También debemos instalar BLAST, pero una versión muy específica: BLAST legacy 2.22 (nunca BLAST+). Esta versión la podemos descargar [aquí](ftp://ftp.ncbi.nlm.nih.gov/blast/executables/legacy.NOTSUPPORTED/2.2.22/). Los archivos que nos interesan están en la carpeta “bin”. Introducir la ruta a esta carpeta en el $PATH del sistema de unix ([ver explicación](https://askubuntu.com/questions/60218/how-to-add-a-directory-to-the-path))

## 3. FASTQ a FASTA

```{bash}
sed -n '1~4s/^@/>/p;2~4p' in.fastq > out.fasta 
```

## 4. Generación de un mapping file

El mapping file es el archivo que usa QIIME para obtener los metadatos. Tiene que tener un formato determinado que se puede consultar [aquí](http://qiime.org/documentation/file_formats.html).

[Aquí también hay un ejemplo de mapping file](http://qiime.org/_static/Examples/File_Formats/Example_Mapping_File.txt).

Lo mejor para generar un mapping file es hacerlo a mano, partiendo de la base de otro y cambiando los metadatos por los de nuestro experimento.

## 5. Validar el mapping file

Existe un comando para validar el mapping file. Recomiendo usarlo, porque este suele ser un paso problemático. El comando corrige errores y genera un output. Yo en cambio recomiendo modificar manualmente el mapping file hasta que no dé erores, y usar nuestro mapping file y no el generado automáticamente por el comando.

El comando es el siguiente:

```{bash}
validate_mapping_file.py -o output_folder -m mapping_file.txt
```

## 6. Crear un fichero con todas las secuencias

QIIME necesita un archivo que contenga todos las secuencias. No obstante, es necesario crearlo con sus herramientas, ya que utiliza etiquetas de secuencias propias y arbritarias. El comando adecuado para hacerlo es [add_qiime_labels](http://qiime.org/scripts/add_qiime_labels.html).

```{bash}
add_qiime_labels.py -m mapping_file.txt -i ../fasta/ -c InputFileName -o combined_seqs.fna
```

Se obtiene el archivo combined_seqs.fna.

## 7. Obtener OTUs "fake"

OTU: operational taxonomic unit. Es una entidad abstracta que se utiliza para trabajar antes de que hayamos asignado la taxonomía de la secuencias. Una OTU engloba todas aquellas sequencias que superan un cierto umbral de similitud (típicamente un 97%, si se trabaja al nivel de especie). Este paso no tiene sentido en secuencias de nanopore: si tenemos un ~10% de error, ninguna secuencia se va a parecer en más de un 97% a otra, aunque procedan del mismo molde de ADN. No obstante, como el pipeline está diseñado de esta manera, el paso no se puede omitir si se quiere continuar.

El pipeline de QIIME utiliza el comando pick_otus.py para este paso. No obstanto, este script va a intentar en vano crear las OTUs, gastando recursos computacionales y tiempo en el proceso. Por ello, podemos generar una tabla de OTUs “fake” con el siguiente script de python. El output imita el formato resultante de pick_otus.py, pero el tiempo de computación es mucho menor.

Para ello se utiliza el script [fakePickOTUs.py](https://github.com/adlape95/ONT-16S-BLAST-and-QIIME/blob/main/fakePickOTUs.py)

```{bash}
python fakePickOTUs.py combined_seqs.fna > combined_seqs_otus.txt
```

El resultado es que se generan tantas OTUs como secuencias hay. Por tanto, se asignará la taxonomía a cada secuencia individual, que es el objetivo de este pipeline.

## 8. Obtener las OTUs representativas

Tradicionalmente esto servía para elegir una secuencia de todas las que forman una OTU como “representativa”. De este modo, asignando la taxonomía a una sola secuencia, se podía asignar la taxonomía a toda la OTU, es decir, a todo el grupo de secuencias. Así se evitaba gastar recursos computacionales asignando la taxonomía de cada secuencia.

De nuevo, este paso no tiene sentido en en este contexto, porque cada OTU está formado por una única secuencia. No obstante, se ejecuta porque es necesario para continuar con el pipeline.

El comando que utilizaremos es [pick_rep_set.py](http://qiime.org/scripts/pick_rep_set.html)

```{bash}
pick_rep_set.py -f combined_seqs.fna -i picked_otus/combined_seqs_otus.txt -o rep_set.fna
```

## 9. Asignar la taxonomía de las secuencias

Este paso coge cada una de las secuencias representativas de cada OTU (recordemos que 1 OTU = 1 secuencia original) y las asigna contra una BB.DD. Como BB.DD. se suele usar SILVA o GreenGenes. Recomendamos SILVA porque está más actualizada.

La BB.DD. de SILVA contiene 16S completos y se puede descargar [aquí](https://www.arb-silva.de/documentation/release-132/)

Vamos a usar el comando [parallel_assign_taxonomy_blast.py](http://qiime.org/scripts/parallel_assign_taxonomy_blast.html), para aprovechar la computación en paralelo con varios hilos y reducir el tiempo de análisis.

Lo ideal es usar tantos hilos como cores o subprocesos disponga tu procesador para sacar el máximo rendimiento. Nunca usaremos más hilos, pues el rendimiento descenderá. Se pueden usar menos hilos si se desea hacer tareas computacionales en paralelo a la ejecución del comando.

```{bash}
parallel_assign_taxonomy_blast.py -i rep_set.fna -t /path/to/SILVA_132_QIIME_release/taxonomy/16S_only/99/consensus_taxonomy_7_levels.txt -r /path/to/SILVA_132_QIIME_release/rep_set/rep_set_16S_only/99/silva_132_99_16S.fna -o blast_tax/ -O 8
```

La opción -O nos deja elegir el número de hilos a usar. Siguiendo los paths de -t y -r podemos saber los archivos de SILVA que son útiles, ya que la descarga de SILVA lleva asociada muchos archivos que no usaremos nunca.

Paciencia: este paso tardará bastante.

## 10. Generar un BIOM table

BIOM es el formato comprimido por excelencia en ecología microbiana. Es binario, así que solo se podría abrir con una herramienta especializada. No obstante, nosotros lo vamos a usar como archivo intermedio.

Vamos a generarlo con el comando [make_otu_table.py](http://qiime.org/scripts/make_otu_table.html):

```{bash}
make_otu_table.py -i picked_otus/combined_seqs_otus.txt -t blast_tax/rep_set_tax_assignments.txt -o otu_table.biom
```

## 11. Generar las tablas de abundancia

Esta herramienta nos permite crear tablas a diferentes niveles taxonómicos a partir del BIOM. Permite generar tanto abundancias absolutas como relativas. Yo recomiendo trabajar con absolutas, porque los datos siempre se puede relativizar de manera sencilla, pero no al revés.

Podemos generar las tablas al nivel taxonómico que prefiramos, pero normalmente vamos a trabajar a nivel de género. Si bien es cierto que podemos generarlo a nivel de especie (el más alto) y luego ir colapsando a niveles inferiores desde [phyloseq](https://joey711.github.io/phyloseq/). Vamos a optar por esta última opción (nivel de especie).

Usamos el comando [summarize_taxa.py](http://qiime.org/scripts/summarize_taxa.html)

```{bash}
summarize_taxa.py -i otu_table.biom -o ./tax -a -L7
```

-a: abundancia absoluta -L: para elegir el nivel. 7 = especie; 6 = género; 5 = familia...

Se generan varios archivos en la carpeta "./tax",. El archivo .txt es el que usaremos para los análisis posteriores en R.
