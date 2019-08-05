from django.shortcuts import render
from django.views.generic import TemplateView
# Spacy, Rdflib librerias
import spacy
import es_core_news_sm
import rdflib
import difflib
from rdflib.serializer import Serializer
from .forms import SbcForm
from collections import OrderedDict
import itertools
from SPARQLWrapper import SPARQLWrapper, JSON


class IndexView(TemplateView):
    '''Metodo que renderiza la plantilla index.html'''
    template_name = 'sbc/index.html'

    def get(self, request):
        form = SbcForm()
        args = {"form": form}
        return render(request, self.template_name, args)

    def post(self, request):
        form = SbcForm(request.POST)
        if form.is_valid():
            # obtiene datos del formulario
            text = form.cleaned_data['consulta']
            semantico = Semantico()
            datos, entidades, datos2 = semantico.consultaVirutoso(text)
            textoAnalizado = semantico.textoHtml(text, entidades)
            form = SbcForm()
            args = {"datos": datos, "form": form,
                    "texto": text, "textoAnalizado": textoAnalizado,
                    "datos2": datos2, "form2": form}
        return render(request, self.template_name, args)


class Tokenizador():
    '''Clase que analiza el texto ingresado por formulario, reconoce entidades y hace consulta sparql por cada entidad encontrada.'''

    def limpiezaDatos(self, text):
        # libreria spacy
        nlp = es_core_news_sm.load()
        text = nlp(text)
        tokenized_sentences = [sentence.text for sentence in text.sents]
        g = rdflib.Graph()
        # nombre del archivo
        g.parse("mydataset.rdf")
        datos = []

        for sentence in tokenized_sentences:
            for entity in nlp(sentence).ents:
                consulta = 'SELECT ?s ?p ?o  WHERE { ?s ?p ?o .FILTER regex(str(?s), "%s") .}' % (
                    entity.text)
                for row in g.query(consulta):
                    tripleta = []
                    predicado = row.p.split("/")
                    objeto = row.o.split("/")
                    predicado = predicado[len(predicado)-1]
                    objeto = objeto[len(objeto)-1]
                    tripleta.append(entity.text)
                    tripleta.append(predicado)
                    tripleta.append(objeto)
                    datos.append(tripleta)
        # elimina duplicados
        datos = OrderedDict((tuple(x), x) for x in datos).values()
        lista = []
        for i in datos:
            lista.append(i)
        return lista


class Semantico():
    sbcEndpoint = SPARQLWrapper("http://localhost:8890/sparql/")
    nlp = es_core_news_sm.load()

    def consultaVirutoso(self, texto):
        text = self.nlp(texto)
        tokenized_sentences = [sentence.text for sentence in text.sents]
        datos = []
        datos2 = []
        entidades = []
        auxiliar = []
        for sentence in tokenized_sentences:
            for entity in self.nlp(sentence).ents:
                palabras = difflib.get_close_matches(entity.text, ['Rafael Correa', 'Odebrecht', 'Alexis Mera', 'CWNE','SK Engeenering'])
                print (palabras)
                palabras2 = ''.join(palabras)

                if len(palabras2) > 0:
                    entidades.append(palabras2)
                    consulta = """
                              SELECT ?s ?p ?o
                             WHERE 
                                { 
                                       ?s ?p ?o .FILTER (regex(str(?s), "%s") || regex(str(?o), "%s")) .
                                }
                            """ % (palabras2.replace(' ',''), palabras2)
                    #print (consulta)
                else:
                    entidades.append(entity.text)
                    consulta = """
                    SELECT ?s ?p ?o
                    WHERE 
                        { 
                            ?s ?p ?o .FILTER (regex(str(?s), "%s") || regex(str(?o), "%s")) .
                        }
                     """ % (entity.text.replace(' ',''), entity)
                # print (type (entity.text))
                
                # print (entity.text)
                #if len(palabras2) > 0:
                    #print (len(palabras2))
                 #   entidades.append(palabras2)
                #else:
                    #print (len(palabras2))
                    #print (palabras2, "here")
                
                #t = entity.text.split(" ")
                #if len(t) > 1:
                 #   print (len(t))
                  #  for i in range(len(t)):
                   #     auxiliar.append(entity.text.split())
                    #    for palabraEn in auxiliar:
                        # consulta mejorada
                       #     print (palabraEn)
                        #    
                         #   consulta = """
                          #      SELECT ?s ?p ?o
                           #     WHERE 
                            #        { 
                             #           ?s ?p ?o .FILTER (regex(str(?s), "%s") || regex(str(?o), "%s")) .
                              #      }
                               # """ % (palabraEn(' ',''), palabraEn)
                #else:
                 #   print ("one token")
                # consulta = """
                #     SELECT ?s ?p ?o
                #     WHERE 
                #         { 
                #             ?s ?p ?o .FILTER (regex(str(?s), "%s") || regex(str(?o), "%s")) .
                #         }
                #      """ % (entity.text.replace(' ',''), entity)

                self.sbcEndpoint.setQuery(consulta)
                self.sbcEndpoint.setReturnFormat(JSON)
                results = self.sbcEndpoint.query().convert()
                for result in results["results"]["bindings"]:
                    lista = []
                    listaTipos = []
                    contador = []
                    listaTipos2 = []
                    listaS = result["s"]["value"].strip()
                    listaP = result["p"]["value"]
                    listaO = result["o"]["value"]
                    # por si sale con ese link no agregar (revisar)
                    # if listaO.startswith('http://www.openlinks'):
                    lista.append(listaS)
                    lista.append(listaP)
                    aux2 = listaP.rsplit('/', 1).pop()
                    if aux2 == "type":
                        #print (listaO," LISTA O")
                        #print (listaS," LISTA S")
                        listaTipos.append(listaO.rsplit('/', 1).pop())
                        listaTipos.append(listaS.rsplit('/', 1).pop())
                    
                    lista.append(listaO)
                    listaTipos2 = [x for x in listaTipos if x != []]
                    datos2.append(listaTipos2)
                    datos2.sort()


                
                #prop.append(entity.label_)
                
                
                    datos.append(lista)
                    #print (datos2)


                
        # Eliminando duplicados
        # entidades = list(set(entidades))
        return datos, entidades, datos2

    def textoHtml(self, texto, entidades):
        for palabra in entidades:
            aux = palabra
            palabraUnica = difflib.get_close_matches(palabra, ['Rafael Correa', 'Odebrecht', 'Alexis Mera', 'CWNE','SK Engeenering'])
            if len(palabraUnica) > 0:
                palabra = ''.join(palabraUnica)

            if len(palabra)>0:
                palabra = palabra.replace(' ', '')
            #print (palabra, " ", aux)
                palabra = palabra.replace('á', 'a')
                palabra = palabra.replace('é', 'e')
                palabra = palabra.replace('í', 'i')
                palabra = palabra.replace('ó', 'o')
                palabra = palabra.replace('ú', 'u')
                url = '<a target="_blank" href = "http://localhost:8080/mydataset/page/{}">{}</a>'.format(palabra,aux)
                if url not in texto:
                    palabra = palabra.replace(' ', '')
                    palabra = palabra.replace('í', 'i')
                    texto = texto.replace(aux, url)
                else:
                    palabra = palabra.replace(' ', '')
                    #print (palabra, " ", aux)
                    palabra = palabra.replace('á', 'a')
                    palabra = palabra.replace('é', 'e')
                    palabra = palabra.replace('í', 'i')
                    palabra = palabra.replace('ó', 'o')
                    palabra = palabra.replace('ú', 'u')
                    url = '<a target="_blank" href = "http://localhost:8080/mydataset/page/{}">{}</a>'.format(palabra,aux)
                    if url not in texto:
                        palabra = palabra.replace(' ', '')
                        palabra = palabra.replace('í', 'i')
                        texto = texto.replace(aux, url)

            else:
                if palabra in texto:

                    if len(palabra) > 0:
                        palabra = palabra.replace(' ', '')
                        #print (palabra, " ", aux)
                        palabra = palabra.replace('á', 'a')
                        palabra = palabra.replace('é', 'e')
                        palabra = palabra.replace('í', 'i')
                        palabra = palabra.replace('ó', 'o')
                        palabra = palabra.replace('ú', 'u')
                        url = '<a target="_blank" href = "http://localhost:8080/mydataset/page/{}">{}</a>'.format(palabra,aux)
                        if url not in texto:
                            palabra = palabra.replace(' ', '')
                            palabra = palabra.replace('í', 'i')
                            texto = texto.replace(aux, url)
                else:
                    palabra = palabra.replace(' ', '')
                    #print (palabra, " ", aux)
                    palabra = palabra.replace('á', 'a')
                    palabra = palabra.replace('é', 'e')
                    palabra = palabra.replace('í', 'i')
                    palabra = palabra.replace('ó', 'o')
                    palabra = palabra.replace('ú', 'u')
                    url = '<a target="_blank" href = "http://localhost:8080/mydataset/page/{}">{}</a>'.format(palabra,aux)
                    if url not in texto:
                        palabra = palabra.replace(' ', '')
                        palabra = palabra.replace('í', 'i')
                        texto = texto.replace(aux, url)
                

        return texto

    def getTipos(self, texto):
        print(texto)

    def consultaPorUri(self, uri):
        consulta = """
                    SELECT ?p ?o
                        WHERE
                        {
                            <%s> ?p  ?o
                        }
                """ % (uri)
        self.sbcEndpoint.setQuery(consulta)
        self.sbcEndpoint.setReturnFormat(JSON)
        results = self.sbcEndpoint.query().convert()
        return results["results"]["bindings"]
