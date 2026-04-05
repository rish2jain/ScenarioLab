'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, TrendingUp, Newspaper, DollarSign, RefreshCw, Settings, Zap } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import type { MarketData, MarketIntelligenceConfig } from '@/lib/types';

export default function MarketIntelPage() {
  const params = useParams();
  const rawId = params.id;
  const simulationId = Array.isArray(rawId) ? rawId[0] : rawId ?? '';

  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const { addToast } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [isConfiguring, setIsConfiguring] = useState(false);
  const [isInjecting, setIsInjecting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [config, setConfig] = useState<MarketIntelligenceConfig>({
    simulation_id: simulationId,
    stock_symbols: ['AAPL', 'MSFT', 'GOOGL'],
    news_queries: ['tech earnings', 'regulatory news', 'M&A activity'],
    refresh_interval: 300,
  });

  useEffect(() => {
    const loadMarketData = async () => {
      setIsLoading(true);
      setLoadError(null);
      try {
        const result = await api.getMarketIntelligenceFeed(simulationId);
        setMarketData(result);
      } catch (error) {
        setMarketData(null);
        setLoadError(
          error instanceof Error
            ? error.message
            : 'Could not load market intelligence.'
        );
      }
      setIsLoading(false);
    };

    loadMarketData();
  }, [simulationId]);

  const handleConfigure = async () => {
    setIsConfiguring(true);
    try {
      await api.configureMarketIntelligence(config);
      addToast('Configuration saved successfully.', 'success');
    } catch {
      addToast('Failed to save configuration.', 'error');
    }
    setIsConfiguring(false);
  };

  const handleInject = async () => {
    setIsInjecting(true);
    try {
      await api.injectMarketIntelligence(simulationId);
      addToast('Data injected into simulation successfully.', 'success');
    } catch {
      addToast('Failed to inject data.', 'error');
    }
    setIsInjecting(false);
  };

  const formatNumber = (num: number) => {
    if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
    return num.toString();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading market intelligence...</div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4 px-4 text-center">
        <div className="text-red-400 max-w-md">{loadError}</div>
        <Button variant="secondary" size="sm" onClick={() => window.location.reload()}>
          Retry
        </Button>
        <Link href={`/simulations/${simulationId}`}>
          <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
            Back to simulation
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col -m-4 md:-m-6">
      {/* Header */}
      <div className="px-4 md:px-6 py-3 md:py-4 border-b border-slate-700 bg-slate-800/50">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3 md:gap-4">
            <Link href={`/simulations/${simulationId}`}>
              <Button variant="ghost" size="sm" leftIcon={<ChevronLeft className="w-4 h-4" />}>
                Back
              </Button>
            </Link>
            <div className="min-w-0">
              <h1 className="text-lg md:text-xl font-bold text-slate-100 truncate">
                Market Intelligence
              </h1>
              <p className="text-xs md:text-sm text-slate-400 truncate">
                Real-time market data and news
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Settings className="w-4 h-4" />}
              onClick={() => setIsConfiguring(!isConfiguring)}
            >
              Configure
            </Button>
            <Button
              size="sm"
              leftIcon={<Zap className="w-4 h-4" />}
              onClick={handleInject}
              isLoading={isInjecting}
            >
              Inject into Simulation
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto p-4 md:p-6">
        <div className="max-w-6xl mx-auto space-y-6">
          {/* Configuration Panel */}
          {isConfiguring && (
            <Card>
              <div className="space-y-4">
                <h3 className="font-semibold text-slate-100">Data Source Configuration</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                      Stock Symbols (comma-separated)
                    </label>
                    <Input
                      value={config.stock_symbols?.join(', ')}
                      onChange={(e) => setConfig({
                        ...config,
                        stock_symbols: e.target.value.split(',').map(s => s.trim()).filter(Boolean),
                      })}
                      placeholder="AAPL, MSFT, GOOGL"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                      News Query Terms
                    </label>
                    <Input
                      value={config.news_queries?.join(', ')}
                      onChange={(e) => setConfig({
                        ...config,
                        news_queries: e.target.value.split(',').map(s => s.trim()).filter(Boolean),
                      })}
                      placeholder="tech earnings, regulatory news"
                    />
                  </div>
                </div>
                <div className="flex justify-end">
                  <Button
                    size="sm"
                    leftIcon={<RefreshCw className="w-4 h-4" />}
                    onClick={handleConfigure}
                    isLoading={isConfiguring}
                  >
                    Save Configuration
                  </Button>
                </div>
              </div>
            </Card>
          )}

          {/* Stock Ticker */}
          <Card
            header={
              <div className="flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-semibold text-slate-100">Stock Prices</h2>
              </div>
            }
          >
            {(!marketData?.stocks || Object.keys(marketData.stocks).length === 0) ? (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <DollarSign className="w-10 h-10 text-slate-600 mb-3" />
                <p className="text-slate-400 font-medium leading-relaxed">
                  No stock data available.
                  <br />
                  <span className="text-sm">Configure market intelligence or inject data to see updates.</span>
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.values(marketData.stocks).map((stock) => (
                  <div key={stock.symbol} className="p-4 bg-slate-700/20 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-lg font-bold text-slate-100">{stock.symbol}</span>
                      {stock.mock && (
                        <span className="text-xs px-2 py-0.5 bg-slate-600/50 rounded text-slate-400">
                          Mock
                        </span>
                      )}
                    </div>
                    <div className="text-2xl font-bold text-slate-100">
                      ${stock.price.toFixed(2)}
                    </div>
                    <div className={`flex items-center gap-1 text-sm ${
                      stock.change >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      <TrendingUp className={`w-4 h-4 ${stock.change < 0 ? 'rotate-180' : ''}`} />
                      <span>
                        {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)} ({stock.change_percent.toFixed(2)}%)
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 mt-2">
                      Vol: {formatNumber(stock.volume)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* News Feed */}
          <Card
            header={
              <div className="flex items-center gap-2">
                <Newspaper className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-semibold text-slate-100">Relevant News</h2>
              </div>
            }
          >
            {(!marketData?.news || marketData.news.length === 0) ? (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <Newspaper className="w-10 h-10 text-slate-600 mb-3" />
                <p className="text-slate-400 font-medium leading-relaxed">
                  No news available.
                  <br />
                  <span className="text-sm">Configure news queries or inject data to see updates.</span>
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {marketData.news.map((article, index) => (
                  <div key={index} className="p-4 bg-slate-700/20 rounded-lg hover:bg-slate-700/30 transition-colors">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <h3 className="font-medium text-slate-200 mb-1">{article.title}</h3>
                        <p className="text-sm text-slate-400 mb-2">{article.description}</p>
                        <div className="flex items-center gap-3 text-xs text-slate-500">
                          <span>{article.source}</span>
                          <span>•</span>
                          <span>{new Date(article.published_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <div className="flex-shrink-0">
                        <div className={`px-2 py-1 rounded text-xs font-medium ${
                          article.relevance_score >= 0.8 ? 'bg-green-500/20 text-green-400' :
                          article.relevance_score >= 0.6 ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-slate-600/20 text-slate-400'
                        }`}>
                          {(article.relevance_score * 100).toFixed(0)}% relevant
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Last Updated */}
          <div className="text-center text-sm text-slate-500">
            Last updated: {marketData?.fetched_at ? new Date(marketData.fetched_at).toLocaleString() : 'Unknown'}
          </div>
        </div>
      </div>
    </div>
  );
}
