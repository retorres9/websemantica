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
            datos, entidades, datos2, entidades2 = semantico.consultaVirutoso(text)
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
        entidades2 = []
        auxiliar = []
        for sentence in tokenized_sentences:
            for entity in self.nlp(sentence).ents:
                entidades2.append(entity.text)
                # print ("sem")
                # print (entity.text)
                palabras = difflib.get_close_matches(entity.text, ['Rafael Correa', 'Odebrecht', 'Alexis Mera', 'CWNE','SK Engeenering'])
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
                    
                else:
                    entidades.append(entity.text)
                    consulta = """
                    SELECT ?s ?p ?o
                    WHERE 
                        { 
                            ?s ?p ?o .FILTER (regex(str(?s), "%s") || regex(str(?o), "%s")) .
                        }
                     """ % (entity.text.replace(' ',''), entity)
                
                #if len(palabras2) > 0:
                    
                 #   entidades.append(palabras2)
                #else:
                    
                
                #t = entity.text.split(" ")
                #if len(t) > 1:
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
                        listaTipos.append(listaO.rsplit('/', 1).pop())
                        listaTipos.append(listaS.rsplit('/', 1).pop())
                    
                    lista.append(listaO)
                    listaTipos2 = [x for x in listaTipos if x != []]
                    datos2.append(listaTipos2)
                    datos2.sort()


                
                #prop.append(entity.label_)
                
                    
                    datos.append(lista)


                
        # Eliminando duplicados
        # entidades = list(set(entidades))
        return datos, entidades, datos2, entidades2

    def textoHtml(self, texto, entidades2):
        aux2=""
        listaObjetos = []
        #print (entidades2)
        for palabra in entidades2:
            if palabra in texto:
                consulta2 = """
                            PREFIX cavr: <http://localhost:8080/mydataset/schema/>
                            SELECT ?s ?o
                            WHERE
                            {
                                ?s cavr:label ?o .
                            }""" 
                self.sbcEndpoint.setQuery(consulta2)
                self.sbcEndpoint.setReturnFormat(JSON)
                results3 = self.sbcEndpoint.query().convert()
                for result in results3["results"]["bindings"]:
                    listaS = result["s"]["value"].strip()
                    listaO = result["o"]["value"].strip()
                    aux2 = listaO.rsplit('/', 1).pop()
                    aux6 = listaS.rsplit('/', 1).pop()
                    listaObjetos.append(aux2)
                listaObjetos = list(set(listaObjetos))
                
                palabraUnica = difflib.get_close_matches(palabra,listaObjetos)
                palabraUnica = ''.join(palabraUnica)
                #print (palabraUnica )
                if len(palabraUnica) > 0:
                    palabra2 = palabraUnica
                    #print ("===================================================================")
                else :
                    palabra = palabra






                
                consulta = """
                            PREFIX cavr: <http://localhost:8080/mydataset/schema/>
                            SELECT ?s ?o
                            WHERE
                            {
                                ?s cavr:label ?o .FILTER (regex(str(?o), "%s")) .
                            }""" % (palabra2)
                print (consulta)
                self.sbcEndpoint.setQuery(consulta)
                self.sbcEndpoint.setReturnFormat(JSON)
                results2 = self.sbcEndpoint.query().convert()
                #print (results2)
                for result in results2["results"]["bindings"]:
                    listaS = result["s"]["value"].strip()
                    aux2 = listaS.rsplit('/', 1).pop()
                #palabra = palabra.replace('í', 'i')
                
                url = '<a href = "{}">{}</a>'.format(listaS,palabra)
                print (url)
                
                if url not in texto:
                    texto = texto.replace(palabra, url)
        

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
