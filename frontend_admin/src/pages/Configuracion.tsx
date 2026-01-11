import { useState, useEffect } from 'react';
import { Header } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useConfig, useUpdateConfig, useLLMModels, useTestLLM } from '@/hooks';
import { toast } from 'sonner';
import {
  Bot,
  Smartphone,
  Settings,
  Save,
  TestTube,
  Loader2,
  CheckCircle,
  XCircle,
  Key,
  Eye,
  EyeOff,
} from 'lucide-react';

export const Configuracion = () => {
  const { data: config, isLoading: configLoading } = useConfig();
  const { data: models } = useLLMModels();
  const { mutate: updateConfig, isPending: isUpdating } = useUpdateConfig();
  const { mutate: testLLM, isPending: isTesting } = useTestLLM();

  const [formData, setFormData] = useState({
    llm_provider: 'openai' as 'openai' | 'google',
    llm_model: 'gpt-4o',
    llm_temperature: 0.7,
    llm_max_tokens: 4000,
    openai_api_key: '',
    google_api_key: '',
  });

  const [showApiKey, setShowApiKey] = useState({
    openai: false,
    google: false,
  });

  const [showApiKeyInput, setShowApiKeyInput] = useState({
    openai: false,
    google: false,
  });

  useEffect(() => {
    if (config) {
      setFormData({
        llm_provider: config.llm_provider,
        llm_model: config.llm_model,
        llm_temperature: config.llm_temperature,
        llm_max_tokens: config.llm_max_tokens,
        openai_api_key: '',
        google_api_key: '',
      });
    }
  }, [config]);

  const handleProviderChange = (provider: 'openai' | 'google') => {
    const defaultModel = provider === 'openai' ? 'gpt-4o' : 'gemini-2.0-flash-exp';
    setFormData({
      ...formData,
      llm_provider: provider,
      llm_model: defaultModel,
    });
  };

  const handleSave = () => {
    const dataToSave: Record<string, unknown> = {
      llm_provider: formData.llm_provider,
      llm_model: formData.llm_model,
      llm_temperature: formData.llm_temperature,
      llm_max_tokens: formData.llm_max_tokens,
    };

    if (formData.openai_api_key) {
      dataToSave.openai_api_key = formData.openai_api_key;
    }
    if (formData.google_api_key) {
      dataToSave.google_api_key = formData.google_api_key;
    }

    updateConfig(dataToSave, {
      onSuccess: () => {
        toast.success('Configuración guardada correctamente');
        setShowApiKeyInput({ openai: false, google: false });
        setFormData((prev) => ({ ...prev, openai_api_key: '', google_api_key: '' }));
      },
      onError: (error) => {
        toast.error(`Error al guardar: ${error.message}`);
      },
    });
  };

  const handleTest = () => {
    testLLM(
      { provider: formData.llm_provider },
      {
        onSuccess: (result) => {
          if (result.success) {
            toast.success('✅ Conexión exitosa con el LLM');
          } else {
            toast.error(`❌ Error: ${result.error}`);
          }
        },
        onError: (error) => {
          toast.error(`Error de conexión: ${error.message}`);
        },
      }
    );
  };

  const availableModels =
    formData.llm_provider === 'openai'
      ? models?.openai || ['gpt-4o', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo']
      : models?.google || ['gemini-2.0-flash-exp', 'gemini-1.5-pro', 'gemini-1.5-flash'];

  if (configLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div>
      <Header title="Configuración" subtitle="Gestiona la configuración del sistema" />

      <div className="p-6">
        <Tabs defaultValue="llm" className="w-full max-w-4xl mx-auto">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="llm" className="flex items-center gap-2">
              <Bot className="w-4 h-4" />
              LLM
            </TabsTrigger>
            <TabsTrigger value="whatsapp" className="flex items-center gap-2">
              <Smartphone className="w-4 h-4" />
              WhatsApp
            </TabsTrigger>
            <TabsTrigger value="general" className="flex items-center gap-2">
              <Settings className="w-4 h-4" />
              General
            </TabsTrigger>
          </TabsList>

          {/* LLM Configuration */}
          <TabsContent value="llm" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bot className="w-5 h-5" />
                  Configuración del Modelo de Lenguaje
                </CardTitle>
                <CardDescription>
                  Configura el proveedor y modelo de IA para el asistente
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Proveedor */}
                <div className="space-y-2">
                  <Label>Proveedor LLM</Label>
                  <Select
                    value={formData.llm_provider}
                    onValueChange={(value) =>
                      handleProviderChange(value as 'openai' | 'google')
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openai">
                        <div className="flex items-center gap-2">
                          <span>🟢 OpenAI</span>
                          {config?.openai_api_key_configured && (
                            <span className="text-xs text-green-600">(✓ Configurado)</span>
                          )}
                        </div>
                      </SelectItem>
                      <SelectItem value="google">
                        <div className="flex items-center gap-2">
                          <span>🔵 Google Gemini</span>
                          {config?.google_api_key_configured && (
                            <span className="text-xs text-green-600">(✓ Configurado)</span>
                          )}
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Modelo */}
                <div className="space-y-2">
                  <Label>Modelo</Label>
                  <Select
                    value={formData.llm_model}
                    onValueChange={(value) =>
                      setFormData({ ...formData, llm_model: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {availableModels.map((model) => (
                        <SelectItem key={model} value={model}>
                          {model}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {formData.llm_provider === 'openai'
                      ? 'Recomendado: gpt-4o (más rápido y económico)'
                      : 'Recomendado: gemini-2.0-flash-exp (última versión)'}
                  </p>
                </div>

                {/* Temperature */}
                <div className="space-y-2">
                  <Label>Temperature: {formData.llm_temperature}</Label>
                  <Slider
                    value={[formData.llm_temperature]}
                    onValueChange={([value]) =>
                      setFormData({ ...formData, llm_temperature: value })
                    }
                    min={0}
                    max={1}
                    step={0.1}
                    className="w-full"
                  />
                  <p className="text-xs text-muted-foreground">
                    Menor = más determinístico | Mayor = más creativo
                  </p>
                </div>

                {/* Max Tokens */}
                <div className="space-y-2">
                  <Label>Max Tokens</Label>
                  <Input
                    type="number"
                    value={formData.llm_max_tokens}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        llm_max_tokens: parseInt(e.target.value) || 4000,
                      })
                    }
                    min={1000}
                    max={8000}
                  />
                </div>

                {/* OpenAI API Key */}
                <div className="space-y-2 p-4 border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Key className="w-4 h-4" />
                      <Label>OpenAI API Key</Label>
                    </div>
                    <div className="flex items-center gap-2">
                      {config?.openai_api_key_configured ? (
                        <span className="text-sm text-green-600 flex items-center gap-1">
                          <CheckCircle className="w-4 h-4" />
                          Configurada
                        </span>
                      ) : (
                        <span className="text-sm text-red-600 flex items-center gap-1">
                          <XCircle className="w-4 h-4" />
                          No configurada
                        </span>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setShowApiKeyInput({
                            ...showApiKeyInput,
                            openai: !showApiKeyInput.openai,
                          })
                        }
                      >
                        {showApiKeyInput.openai ? 'Cancelar' : 'Cambiar'}
                      </Button>
                    </div>
                  </div>

                  {showApiKeyInput.openai && (
                    <div className="relative mt-2">
                      <Input
                        type={showApiKey.openai ? 'text' : 'password'}
                        placeholder="sk-proj-..."
                        value={formData.openai_api_key}
                        onChange={(e) =>
                          setFormData({ ...formData, openai_api_key: e.target.value })
                        }
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute right-2 top-1/2 -translate-y-1/2"
                        onClick={() =>
                          setShowApiKey({ ...showApiKey, openai: !showApiKey.openai })
                        }
                      >
                        {showApiKey.openai ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                  )}
                </div>

                {/* Google API Key */}
                <div className="space-y-2 p-4 border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Key className="w-4 h-4" />
                      <Label>Google API Key</Label>
                    </div>
                    <div className="flex items-center gap-2">
                      {config?.google_api_key_configured ? (
                        <span className="text-sm text-green-600 flex items-center gap-1">
                          <CheckCircle className="w-4 h-4" />
                          Configurada
                        </span>
                      ) : (
                        <span className="text-sm text-red-600 flex items-center gap-1">
                          <XCircle className="w-4 h-4" />
                          No configurada
                        </span>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setShowApiKeyInput({
                            ...showApiKeyInput,
                            google: !showApiKeyInput.google,
                          })
                        }
                      >
                        {showApiKeyInput.google ? 'Cancelar' : 'Cambiar'}
                      </Button>
                    </div>
                  </div>

                  {showApiKeyInput.google && (
                    <div className="relative mt-2">
                      <Input
                        type={showApiKey.google ? 'text' : 'password'}
                        placeholder="AIzaSy..."
                        value={formData.google_api_key}
                        onChange={(e) =>
                          setFormData({ ...formData, google_api_key: e.target.value })
                        }
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute right-2 top-1/2 -translate-y-1/2"
                        onClick={() =>
                          setShowApiKey({ ...showApiKey, google: !showApiKey.google })
                        }
                      >
                        {showApiKey.google ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                  )}
                </div>

                {/* Alertas */}
                {formData.llm_provider === 'openai' && !config?.openai_api_key_configured && (
                  <Alert variant="destructive">
                    <AlertDescription>
                      ⚠️ Debes configurar tu OpenAI API Key para usar este proveedor
                    </AlertDescription>
                  </Alert>
                )}

                {formData.llm_provider === 'google' && !config?.google_api_key_configured && (
                  <Alert variant="destructive">
                    <AlertDescription>
                      ⚠️ Debes configurar tu Google API Key para usar este proveedor
                    </AlertDescription>
                  </Alert>
                )}

                {/* Botones */}
                <div className="flex gap-2 pt-4 border-t">
                  <Button onClick={handleSave} disabled={isUpdating}>
                    {isUpdating ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Guardando...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-2" />
                        Guardar Cambios
                      </>
                    )}
                  </Button>

                  <Button variant="outline" onClick={handleTest} disabled={isTesting}>
                    {isTesting ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Probando...
                      </>
                    ) : (
                      <>
                        <TestTube className="w-4 h-4 mr-2" />
                        Probar Conexión
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* WhatsApp Configuration */}
          <TabsContent value="whatsapp" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Smartphone className="w-5 h-5" />
                  Configuración WhatsApp
                </CardTitle>
                <CardDescription>Configuración de la integración con WhatsApp</CardDescription>
              </CardHeader>
              <CardContent>
                <Alert>
                  <AlertDescription className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    Estado: {config?.whatsapp_configured ? 'Conectado (Simulación)' : 'No configurado'}
                  </AlertDescription>
                </Alert>
                <p className="text-sm text-muted-foreground mt-4">
                  La configuración de WhatsApp Business API estará disponible próximamente.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* General Configuration */}
          <TabsContent value="general" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  Configuración General
                </CardTitle>
                <CardDescription>Configuración general del sistema</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Configuraciones adicionales estarán disponibles próximamente.
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

