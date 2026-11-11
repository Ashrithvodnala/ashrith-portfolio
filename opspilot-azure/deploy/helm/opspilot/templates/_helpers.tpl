{{- define "opspilot.name" -}}opspilot{{- end -}}

{{- define "opspilot.labels" -}}
app.kubernetes.io/name: {{ include "opspilot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "opspilot.selector" -}}
app.kubernetes.io/name: {{ include "opspilot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "opspilot.env" -}}
- name: LLM_PROVIDER
  value: {{ .Values.llm.provider | quote }}
- name: AZURE_OPENAI_ENDPOINT
  value: {{ .Values.llm.azureEndpoint | quote }}
- name: AZURE_OPENAI_API_VERSION
  value: {{ .Values.llm.apiVersion | quote }}
- name: CHAT_MODEL
  value: {{ .Values.llm.chatModel | quote }}
- name: EMBEDDING_MODEL
  value: {{ .Values.llm.embeddingModel | quote }}
- name: EMBEDDING_DIM
  value: {{ .Values.llm.embeddingDim | quote }}
- name: TOP_K
  value: {{ .Values.rag.topK | quote }}
- name: MAX_DISTANCE
  value: {{ .Values.rag.maxDistance | quote }}
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ .Values.database.existingSecret }}
      key: {{ .Values.database.key }}
- name: ADMIN_TOKEN
  valueFrom:
    secretKeyRef:
      name: {{ .Values.adminToken.existingSecret }}
      key: {{ .Values.adminToken.key }}
      optional: true
{{- end -}}
