import speech_recognition as sr
import subprocess
import os
import dialogflow_v2 as dialogflow


class NLP:
    

    def init(self,filename_src,filename_out,language):
        self.converttowav(filename_src,filename_out)

        r=sr.Recognizer()

        with sr.WavFile(filename_out) as source:
            print("Speak anything: ")
            audio= r.record(source)
        try:
            language1=self.getLanguage(language,1)
            text= r.recognize_google(audio,language=self.getLanguage(language,1))
            print(text)
        except:
            print("Sorry")

        respuesta=self.detect_intent_texts('telegramtranscription-qypmiv','125',text,self.getLanguage(language,2))
        #print(respuesta)
        return respuesta
    
    def converttowav(self,filename_src,filename_out):
        process = subprocess.run(['ffmpeg', '-y', '-i', filename_src, filename_out])


    def detect_intent_texts(self, project_id, session_id, texts, language_code):
        """Returns the result of detect intent with texts as inputs.

        Using the same `session_id` between requests allows continuation
        of the conversation."""
        
        session_client = dialogflow.SessionsClient()

        session = session_client.session_path(project_id, session_id)

        text_input = dialogflow.types.TextInput(text=texts, language_code=language_code)

        query_input = dialogflow.types.QueryInput(text=text_input)

        response = session_client.detect_intent(session=session, query_input=query_input)

    
        return response.query_result

    def text_input(self, text,language):
        respuesta=self.detect_intent_texts('telegramtranscription-qypmiv','125',text,self.getLanguage(language,2))
        return respuesta

    def getLanguage(self,language_in,type):
        if language_in=='esp':
            if(type==1): 
                return 'es-ES'
            else: 
                return 'es'
        else:
            if(type==1): 
                return 'en-US'
            else: 
                return 'en'